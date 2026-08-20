from django.urls import path
from . import views

urlpatterns = [
    path('', views.work_page, name='work_page'),
    path('api/messages/', views.api_messages, name='work_api_messages'),
    path('api/send/', views.api_send, name='work_api_send'),
    path('api/scholar/', views.api_scholar, name='work_api_scholar'),
]
