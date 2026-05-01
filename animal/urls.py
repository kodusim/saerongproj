from django.urls import path
from . import views

urlpatterns = [
    path('', views.animal_view, name='animal_view'),
    path('login/', views.animal_login, name='animal_login'),
    path('logout/', views.animal_logout, name='animal_logout'),
    # API
    path('api/members/', views.member_list_api, name='animal_member_list'),
    path('api/members/create/', views.member_create_api, name='animal_member_create'),
    path('api/members/reorder/', views.member_reorder_api, name='animal_member_reorder'),
    path('api/members/<int:member_id>/', views.member_detail_api, name='animal_member_detail'),
]
