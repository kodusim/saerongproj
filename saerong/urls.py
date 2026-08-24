from django.apps import apps
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import (
    dashboard, category_detail, subcategory_detail, game_notices,
    beta_view, beta_logout,
)

urlpatterns = [
    path("", dashboard, name="dashboard"),  # 메인 대시보드
    path("beta/", beta_view, name="beta_view"),  # 창업시장 베타 (admin/admin)
    path("beta", beta_view),  # trailing slash 없는 변형도 허용
    path("beta/logout/", beta_logout, name="beta_logout"),
    path("category/<slug:slug>/", category_detail, name="category_detail"),  # 대분류 상세
    path("subcategory/<slug:slug>/", subcategory_detail, name="subcategory_detail"),  # 중분류 상세
    path("games/", game_notices, name="game_notices"),  # 게임 공지사항
    path("admin/", admin.site.urls),
    path("summernote/", include("django_summernote.urls")),  # Summernote 에디터
    path("api/", include("api.urls")),  # API 엔드포인트
    path("tdmprediction/", include("tdm.urls")),  # 반코마이신 TDM 하이브리드 예측
    path("work/", include("work.urls")),  # Work — 실시간 채팅 + 구글 스칼라 검색 (초안)
]

# 개발 환경에서 미디어 파일 서빙 설정
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if apps.is_installed("debug_toolbar"):
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
