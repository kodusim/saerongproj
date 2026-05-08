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
    path('api/collectibles/items/create/', views.collectible_item_create_api, name='animal_collectible_item_create'),
    path('api/collectibles/items/<int:item_id>/', views.collectible_item_delete_api, name='animal_collectible_item_delete'),
    path('api/equips/', views.equips_api, name='animal_equips'),
    path('api/equips/set/', views.equip_set_api, name='animal_equip_set'),
    path('api/equips/slots/create/', views.equip_slot_create_api, name='animal_equip_slot_create'),
    path('api/equips/slots/<int:slot_id>/', views.equip_slot_delete_api, name='animal_equip_slot_delete'),
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
    path('api/boss/clears/<int:clear_id>/participants/add/', views.boss_clear_participant_add_api, name='animal_boss_clear_part_add'),
    path('api/boss/clears/<int:clear_id>/participants/<int:member_id>/', views.boss_clear_participant_remove_api, name='animal_boss_clear_part_remove'),
    # 정산
    path('api/settle/', views.settle_api, name='animal_settle'),
    path('api/settle/save/', views.settle_save_api, name='animal_settle_save'),
    # 자금 출납
    path('api/cash/', views.cash_list_api, name='animal_cash_list'),
    path('api/cash/create/', views.cash_create_api, name='animal_cash_create'),
    path('api/cash/<int:entry_id>/', views.cash_detail_api, name='animal_cash_detail'),
    # 방문 로그
    path('api/visit-log/', views.visit_log_api, name='animal_visit_log'),
]
