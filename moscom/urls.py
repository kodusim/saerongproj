from django.urls import path
from . import views

urlpatterns = [
    path('devices/', views.device_list, name='moscom_db_device_list'),
    path('devices/<int:device_id>/', views.device_update, name='moscom_db_device_update'),
    path('collections/', views.collections, name='moscom_db_collections'),
    path('collections/<int:collection_id>/', views.collection_detail, name='moscom_db_collection_detail'),
    path('sync-status/', views.sync_status, name='moscom_db_sync_status'),
    path('edit-logs/', views.edit_logs, name='moscom_db_edit_logs'),
]
