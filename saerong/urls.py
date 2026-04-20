from django.apps import apps
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import (
    dashboard, category_detail, subcategory_detail, game_notices, mosquito_test,
    moscom_devices, moscom_raw_collection, moscom_statistics, moscom_hourly,
    moscom_daily, moscom_predict, moscom_complaint_risk,
    mosquito_logout, moscom_my_devices, moscom_users_api, moscom_user_detail_api,
    moscom_remedy_methods, moscom_remedy_api, moscom_remedy_detail_api,
    moscom_equipment_health, moscom_admin_judgment,
    moscom_report_api, moscom_report_detail_api, mosquito_report_view,
    moscom_overview,
)
from django.views.decorators.csrf import csrf_exempt

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
    path("mosquito-test/api/predict/", moscom_predict, name="moscom_predict"),  # AI 모기 발생 예측
    path("mosquito-test/api/complaint-risk/", moscom_complaint_risk, name="moscom_complaint_risk"),  # 민원 위험 점수
    path("mosquito-test/logout/", mosquito_logout, name="mosquito_logout"),
    path("mosquito-test/api/my-devices/", moscom_my_devices, name="moscom_my_devices"),
    path("mosquito-test/api/admin/users/", csrf_exempt(moscom_users_api), name="moscom_users_api"),
    path("mosquito-test/api/admin/users/<str:login_id>/", csrf_exempt(moscom_user_detail_api), name="moscom_user_detail_api"),
    path("mosquito-test/api/remedy/methods/", moscom_remedy_methods, name="moscom_remedy_methods"),
    path("mosquito-test/api/remedy/", csrf_exempt(moscom_remedy_api), name="moscom_remedy_api"),
    path("mosquito-test/api/remedy/<str:plan_id>/", csrf_exempt(moscom_remedy_detail_api), name="moscom_remedy_detail_api"),
    path("mosquito-test/api/equipment-health/", moscom_equipment_health, name="moscom_equipment_health"),
    path("mosquito-test/api/overview/", moscom_overview, name="moscom_overview"),
    path("mosquito-test/api/admin-judgment/", moscom_admin_judgment, name="moscom_admin_judgment"),
    path("mosquito-test/api/report/", csrf_exempt(moscom_report_api), name="moscom_report_api"),
    path("mosquito-test/api/report/<str:report_id>/", csrf_exempt(moscom_report_detail_api), name="moscom_report_detail_api"),
    path("mosquito-test/report/<str:report_id>/", mosquito_report_view, name="mosquito_report_view"),
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