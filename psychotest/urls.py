from django.urls import path
from . import views

app_name = "psychotest"

urlpatterns = [
    path('tests/', views.test_list, name='test_list'),  # 테스트 목록
    path('tests/<int:test_id>/', views.test_detail, name='test_detail'),  # 테스트 상세
    path('tests/<int:test_id>/take/', views.take_test, name='take_test'),  # 테스트 진행
    path('tests/<int:test_id>/result/', views.test_result, name='test_result'),  # 테스트 결과
]