from django.urls import path
from . import views

app_name = "psychotest"

urlpatterns = [
    path('tests/', views.test_list, name='test_list'),  # 테스트 목록
    path('tests/<int:test_id>/', views.test_detail, name='test_detail'),  # 테스트 상세
    path('tests/<int:test_id>/take/', views.take_test, name='take_test'),  # 테스트 진행
    path('tests/<int:test_id>/question/<int:question_id>/answer/', views.answer_question, name='answer_question'),  # 질문 응답 처리
    path('tests/<int:test_id>/calculate/', views.calculate_result, name='calculate_result'),  # 결과 계산
    path('tests/<int:test_id>/result/', views.test_result, name='test_result'),  # 테스트 결과
    path('tests/<int:test_id>/intro/', views.test_intro, name='test_intro'),  #메인 이미지
]