from django.urls import path
from . import views

app_name = "community"

urlpatterns = [
    path('', views.category_list, name='category_list'),
    path('<slug:category_slug>/', views.post_list, name='category_detail'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
]