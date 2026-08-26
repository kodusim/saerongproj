"""saerong.com — FastAPI 애플리케이션.

라우트
  /                     랜딩
  /tdmprediction/*      반코마이신 TDM 하이브리드 예측
  /work/*               채팅 · 게시판
  /bltest/*             소설 연재 플랫폼 (프로토타입)
  /healthz              헬스체크

정적/미디어 파일은 운영에서 nginx 가 직접 서빙한다 (`/static`, `/media`).
DEBUG 일 때만 앱이 대신 마운트한다.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR, settings
from app.routers import bl, farm, tdm, work
from app.security import CsrfMiddleware
from app.templating import templates

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title='saerong.com',
    docs_url='/api/docs' if settings.debug else None,
    redoc_url=None,
    openapi_url='/api/openapi.json' if settings.debug else None,
)

# 미들웨어는 나중에 추가된 것이 먼저 실행된다 — 세션이 CSRF 보다 바깥이어야 한다.
app.add_middleware(CsrfMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie,
    same_site='lax',
    https_only=not settings.debug,
    max_age=60 * 60 * 24 * 14,
)

app.include_router(tdm.router)
app.include_router(work.router)
app.include_router(farm.router)
app.include_router(bl.router)


@app.get('/', response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(request, 'landing.html', {})


@app.get('/healthz', response_class=PlainTextResponse)
async def healthz():
    return 'ok'


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """API 경로는 JSON, 페이지 경로는 HTML 로 응답한다."""
    if request.url.path.startswith('/api') or '/api/' in request.url.path:
        return JSONResponse({'error': exc.detail}, status_code=exc.status_code)
    return templates.TemplateResponse(
        request,
        'error.html',
        {'status_code': exc.status_code, 'detail': exc.detail},
        status_code=exc.status_code,
    )


if settings.debug:
    app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'static')), name='static')
    settings.media_root.mkdir(parents=True, exist_ok=True)
    app.mount('/media', StaticFiles(directory=str(settings.media_root)), name='media')
