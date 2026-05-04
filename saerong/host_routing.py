"""호스트 기반 라우팅 미들웨어.

moscom.ai / www.moscom.ai 로 들어온 요청은 다음과 같이 변환:
- "/" → "/mosquito-test/"  (URL은 그대로 / 인 것처럼 보이지만 실제 view는 mosquito_test)
- "/category/..", "/animal/.." 등 saerong 전용 경로는 404

같은 서버 / 같은 코드 / 같은 DB 위에서 호스트만 다르게 보이게 하는 단순한 가상호스트 처리.
"""
from django.http import HttpResponseNotFound
from django.conf import settings


# moscom.ai에서 노출할 prefix — mosquito-test 와 같이 그 하위 API/링크들이 필요하다.
ALLOWED_PREFIXES = (
    '/mosquito-test',
    '/static/',
    '/media/',
    '/admin/',  # 관리자 들어가야 할 수도 있으니 열어둠
    '/__debug__/',
)


def _is_moscom_host(request):
    host = (request.get_host() or '').split(':', 1)[0].lower()
    moscom_hosts = getattr(settings, 'MOSCOM_HOSTS', set())
    return host in moscom_hosts


class MoscomHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if _is_moscom_host(request):
            path = request.path or '/'
            # 루트("/") 진입 → mosquito-test 페이지 view 가 처리하도록 path_info 를 다시 씀
            if path == '/' or path == '':
                request.path = '/mosquito-test/'
                request.path_info = '/mosquito-test/'
            else:
                # mosquito-test 외 경로는 차단 (단, 정적/미디어/관리자 허용)
                if not any(path.startswith(p) for p in ALLOWED_PREFIXES):
                    return HttpResponseNotFound(
                        b'<!DOCTYPE html><html><head><meta charset="utf-8">'
                        b'<title>Not Found</title></head><body style="font-family:sans-serif;padding:40px">'
                        b'<h1>404 Not Found</h1>'
                        b'<p>This page does not exist on moscom.ai.</p>'
                        b'<p><a href="/">\xea\xb0\x80\xea\xb8\xb0</a></p>'
                        b'</body></html>'
                    )
        return self.get_response(request)
