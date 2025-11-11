from django.apps import apps
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import dashboard, game_notices

urlpatterns = [
    path("", dashboard, name="dashboard"),  # 메인 대시보드
    path("games/", game_notices, name="game_notices"),  # 게임 공지사항
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),  # API 엔드포인트
]

# 개발 환경에서 미디어 파일 서빙 설정
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if apps.is_installed("debug_toolbar"):
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]