from django.urls import path
from . import views

app_name = 'facetest'

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload_image, name='upload_image'),
    path('result/<uuid:result_id>/', views.result_detail, name='result_detail'),
    path('share/<uuid:result_id>/', views.share_result, name='share_result'),
]