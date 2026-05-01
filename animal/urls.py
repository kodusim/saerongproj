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
    path('api/collectibles/', views.collectibles_api, name='animal_collectibles'),
    path('api/collectibles/toggle/', views.collectible_toggle_api, name='animal_collectible_toggle'),
    path('api/equips/', views.equips_api, name='animal_equips'),
    path('api/equips/set/', views.equip_set_api, name='animal_equip_set'),
    # 보스
    path('api/boss/list/', views.boss_list_api, name='animal_boss_list'),
    path('api/boss/create/', views.boss_create_api, name='animal_boss_create'),
    path('api/boss/<int:boss_id>/', views.boss_detail_api, name='animal_boss_detail'),
    path('api/boss/weeks/', views.week_list_api, name='animal_boss_weeks'),
    path('api/boss/weeks/create/', views.week_create_api, name='animal_boss_week_create'),
    path('api/boss/weeks/close/', views.week_close_api, name='animal_boss_week_close'),
    path('api/boss/clears/', views.boss_clears_api, name='animal_boss_clears'),
    path('api/boss/clears/ingest/', views.boss_clear_ingest_api, name='animal_boss_clear_ingest'),
    path('api/boss/clears/<int:clear_id>/', views.boss_clear_detail_api, name='animal_boss_clear_detail'),
]
