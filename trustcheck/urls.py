from django.urls import path
from . import views

urlpatterns = [
    # 페이지
    path('', views.landing, name='tc_landing'),
    path('app/', views.app_page, name='tc_app'),

    # 인증
    path('api/signup/', views.api_signup, name='tc_signup'),
    path('api/login/', views.api_login, name='tc_login'),
    path('api/logout/', views.api_logout, name='tc_logout'),
    path('api/me/', views.api_me, name='tc_me'),

    # 상담 게시글 + 역매칭
    path('api/posts/', views.api_posts, name='tc_posts'),
    path('api/posts/<int:post_id>/', views.api_post_detail, name='tc_post_detail'),
    path('api/posts/<int:post_id>/appeal/', views.api_appeal, name='tc_appeal'),
    path('api/appeals/<int:appeal_id>/respond/', views.api_appeal_respond, name='tc_appeal_respond'),

    # 채팅
    path('api/rooms/<int:room_id>/', views.api_room, name='tc_room'),
    path('api/rooms/<int:room_id>/send/', views.api_room_send, name='tc_room_send'),

    # 상품 / 결제 / 케이스
    path('api/products/', views.api_products, name='tc_products'),
    path('api/checkout/', views.api_checkout, name='tc_checkout'),
    path('api/cases/', views.api_cases, name='tc_cases'),
    path('api/cases/<int:case_id>/', views.api_case_detail, name='tc_case_detail'),
    path('api/cases/<int:case_id>/update/', views.api_case_update, name='tc_case_update'),
    path('api/cases/<int:case_id>/report/', views.api_report_create, name='tc_report_create'),

    # 관리자
    path('api/admin/experts/', views.api_admin_experts, name='tc_admin_experts'),
    path('api/admin/experts/<int:expert_id>/approve/', views.api_admin_expert_approve, name='tc_admin_expert_approve'),
]
