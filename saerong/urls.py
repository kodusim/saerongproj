from django.apps import apps
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import (
    dashboard, category_detail, subcategory_detail, game_notices, mosquito_test,
    moscom_devices, moscom_raw_collection, moscom_statistics, moscom_hourly,
    moscom_daily,
)

urlpatterns = [
    path("", dashboard, name="dashboard"),  # 메인 대시보드
    path("category/<slug:slug>/", category_detail, name="category_detail"),  # 대분류 상세
    path("subcategory/<slug:slug>/", subcategory_detail, name="subcategory_detail"),  # 중분류 상세
    path("mosquito-test/", mosquito_test, name="mosquito_test"),  # 모기 테스트
    path("mosquito-test/api/devices/", moscom_devices, name="moscom_devices"),  # MOSCOM 장비 목록 프록시
    path("mosquito-test/api/raw-collection/", moscom_raw_collection, name="moscom_raw_collection"),  # MOSCOM 포집 데이터 프록시
    path("mosquito-test/api/statistics/", moscom_statistics, name="moscom_statistics"),  # MOSCOM 통계 프록시
    path("mosquito-test/api/hourly/", moscom_hourly, name="moscom_hourly"),  # MOSCOM 시간별(raw) 프록시
    path("mosquito-test/api/daily/", moscom_daily, name="moscom_daily"),  # MOSCOM 일별 집계 (임의 기간)
    path("games/", game_notices, name="game_notices"),  # 게임 공지사항
    path("admin/", admin.site.urls),
    path("summernote/", include("django_summernote.urls")),  # Summernote 에디터
    path("api/", include("api.urls")),  # API 엔드포인트
]

# 개발 환경에서 미디어 파일 서빙 설정
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if apps.is_installed("debug_toolbar"):
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]