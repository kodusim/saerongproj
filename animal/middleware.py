"""/animal/ 페이지 방문 로그 미들웨어.
페이지(HTML) 방문만 기록. API/정적 파일은 제외. 7일 이전 로그는 게으르게 정리.
"""
import time
from datetime import timedelta

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


# 마지막 정리 시각 (메모리 캐시) — 모든 요청에서 매번 정리 쿼리 돌리지 않게
_LAST_SWEEP = {'ts': 0.0}
_SWEEP_INTERVAL_SEC = 60 * 30  # 30분에 한 번씩만 정리


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _maybe_sweep():
    now = time.time()
    if now - _LAST_SWEEP['ts'] < _SWEEP_INTERVAL_SEC:
        return
    _LAST_SWEEP['ts'] = now
    try:
        from .models import VisitLog
        cutoff = timezone.now() - timedelta(days=7)
        VisitLog.objects.filter(ts__lt=cutoff).delete()
    except Exception:
        pass


class VisitLogMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        try:
            path = request.path or ''
            # /animal/ 페이지 방문만 — login/logout/API 제외
            if not path.startswith('/animal/') and path != '/animal':
                return response
            if path.startswith('/animal/api/'):
                return response
            if path.startswith('/animal/login') or path.startswith('/animal/logout'):
                return response
            # 페이지 응답만 (HTML)
            ct = (response.get('Content-Type') or '').lower()
            if 'text/html' not in ct:
                return response
            # 200 / 304만 기록
            if response.status_code not in (200, 304):
                return response

            from .models import VisitLog
            VisitLog.objects.create(
                path=path[:200],
                ip=_client_ip(request)[:64],
                user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:300],
                referer=(request.META.get('HTTP_REFERER') or '')[:300],
                is_admin=bool(request.session.get('animal_admin')),
            )
            _maybe_sweep()
        except Exception:
            # 로깅 실패가 페이지 응답을 막지 않게
            pass
        return response
