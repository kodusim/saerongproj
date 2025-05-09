from django.urls import path
from . import views

app_name = "facetest"

urlpatterns = [
    path('', views.index, name='index'),
    path('analyze/', views.analyze_face, name='analyze_face'),
    path('result/', views.result, name='result'),
    path('result/<uuid:uuid>/', views.result_detail, name='result_detail'),  # 추가: UUID로 결과 조회
    
    # 관리자 페이지
    path('admin/test/<int:test_id>/', views.manage_test, name='manage_test'),
    
    # 결과 유형 관리 API
    path('admin/result-type/<int:type_id>/get-info/', views.get_result_type_info, name='get_result_type_info'),
    path('admin/result-type/<int:type_id>/update/', views.update_result_type, name='update_result_type'),
    path('admin/result-type/<int:type_id>/upload-image/', views.upload_result_image, name='upload_result_image'),
    path('admin/result-image/<int:image_id>/delete/', views.delete_result_image, name='delete_result_image'),
    path('admin/result-image/<int:image_id>/set-main/', views.set_main_image, name='set_main_image'),
    
    # 통합 관리 페이지
    path('admin/test/<int:test_id>/bulk-manage/', views.bulk_manage_result_types, name='bulk_manage_result_types'),
    path('admin/result-type/<int:type_id>/update-sub-image/', views.update_sub_image, name='update_sub_image'),
    path('admin/result-type/<int:type_id>/delete-sub-image/', views.delete_sub_image, name='delete_sub_image'),
    path('tests/', views.test_list, name='test_list'),
    path('tests/<int:test_id>/', views.test_intro, name='test_intro'),
    path('test/<int:test_id>/', views.test_view, name='test'),
    path('result/<uuid:uuid>/', views.result_detail, name='result_detail'),
]