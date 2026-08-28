"""세션 인증 + CSRF.

세션은 Starlette `SessionMiddleware`(서명된 쿠키)를 쓴다 — Django 의
`request.session` 과 사용감이 같다.

CSRF 는 Django 와 호환되는 double-submit 방식이다: `csrftoken` 쿠키를 내려주고
안전하지 않은 메서드에서 `X-CSRFToken` 헤더가 그 값과 같은지 본다. 기존 프런트가
이미 그렇게 보내고 있어서 JS 를 고치지 않아도 그대로 동작한다.

폼 전송(로그인)은 헤더를 못 붙이므로 미들웨어에서 건너뛰고, 라우트 안에서
`csrfmiddlewaretoken` 필드를 직접 검증한다 — 미들웨어에서 body 를 읽으면
다운스트림이 다시 읽을 수 없기 때문이다.
"""
import secrets

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import HTTPConnection

from app.config import settings

CSRF_ERROR = 'CSRF 검증에 실패했습니다. 페이지를 새로고침한 뒤 다시 시도하세요.'

SAFE_METHODS = frozenset({'GET', 'HEAD', 'OPTIONS', 'TRACE'})

# 헤더를 붙일 수 없거나 Django 에서 csrf_exempt 였던 경로
CSRF_EXEMPT_PATHS = frozenset({
    '/tdmprediction/login/',       # 폼 전송 — 라우트에서 직접 검증
    '/tdmprediction/api/predict/',  # Django 에서도 csrf_exempt
    '/bltest/login',               # 폼 전송 — 라우트에서 직접 검증
})

TDM_SESSION_KEY = 'tdm_authed'
TDM_LOGIN_ID_KEY = 'tdm_login_id'

# /bltest — 로그인한 계정 아이디를 담는다 (TDM 세션과 서로 독립이다)
BL_SESSION_KEY = 'bl_login_id'


def new_csrf_token() -> str:
    return secrets.token_hex(32)


class CsrfMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cookie_token = request.cookies.get(settings.csrf_cookie) or ''
        issued = cookie_token or new_csrf_token()
        # 템플릿에서 {{ csrf_token }} 으로 쓸 수 있게 노출
        request.state.csrf_token = issued

        if (
            request.method not in SAFE_METHODS
            and request.url.path not in CSRF_EXEMPT_PATHS
        ):
            sent = request.headers.get('x-csrftoken') or ''
            if not cookie_token or not secrets.compare_digest(sent, cookie_token):
                # 미들웨어에서 raise 한 예외는 FastAPI 핸들러를 타지 않으므로
                # 응답을 직접 돌려준다.
                return JSONResponse(
                    {'error': CSRF_ERROR}, status_code=status.HTTP_403_FORBIDDEN
                )

        response = await call_next(request)

        if not cookie_token:
            response.set_cookie(
                settings.csrf_cookie,
                issued,
                max_age=60 * 60 * 24 * 365,
                samesite='lax',
                secure=not settings.debug,
                httponly=False,  # JS 가 읽어서 헤더로 되돌려줘야 한다
            )
        return response


def verify_form_csrf(request: Request, token: str | None) -> None:
    """폼 전송용 CSRF 검증 (미들웨어가 건너뛴 경로에서 호출)."""
    cookie_token = request.cookies.get(settings.csrf_cookie) or ''
    if not cookie_token or not secrets.compare_digest(token or '', cookie_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=CSRF_ERROR)


def is_tdm_authed(request: Request) -> bool:
    return bool(request.session.get(TDM_SESSION_KEY))


def tdm_login_id(request: Request) -> str:
    return request.session.get(TDM_LOGIN_ID_KEY, '') or ''


def client_ip(conn: HTTPConnection) -> str | None:
    """nginx 뒤에 있으므로 X-Forwarded-For 를 먼저 본다.

    Request 와 WebSocket 둘 다 받는다 (공통 상위 타입이 HTTPConnection).
    """
    xff = conn.headers.get('x-forwarded-for')
    if xff:
        return xff.split(',')[0].strip()
    return conn.client.host if conn.client else None
