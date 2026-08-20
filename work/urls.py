from django.urls import path
from . import views

urlpatterns = [
    path('', views.work_page, name='work_page'),
    path('api/messages/', views.api_messages, name='work_api_messages'),
    path('api/send/', views.api_send, name='work_api_send'),
    path('api/scholar/', views.api_scholar, name='work_api_scholar'),
    path('api/posts/', views.api_posts, name='work_api_posts'),
    path('api/posts/create/', views.api_post_create, name='work_api_post_create'),
    path('api/posts/<int:post_id>/', views.api_post_detail, name='work_api_post_detail'),
]
