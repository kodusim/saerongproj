from django.apps import apps
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from saerong.views import landing

urlpatterns = [
    path("", landing, name="landing"),  # 루트 랜딩
    path("admin/", admin.site.urls),
    path("tdmprediction/", include("tdm.urls")),  # 반코마이신 TDM 하이브리드 예측
    path("work/", include("work.urls")),  # Work — 실시간 채팅 + 구글 스칼라 검색 + 게시판
]

# 개발 환경에서 미디어 파일 서빙 설정
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if apps.is_installed("debug_toolbar"):
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
