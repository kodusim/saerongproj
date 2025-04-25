from django.urls import path
from . import views

app_name = "facetest"

urlpatterns = [
    path('', views.index, name='index'),
    # 관리자 페이지
    path('admin/test/<int:test_id>/', views.manage_test, name='manage_test'),
    path('admin/result-type/<int:type_id>/update/', views.update_result_type, name='update_result_type'),
    path('admin/result-type/<int:type_id>/upload-image/', views.upload_result_image, name='upload_result_image'),
    path('admin/result-image/<int:image_id>/delete/', views.delete_result_image, name='delete_result_image'),
]