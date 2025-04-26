from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("views-stats/", views.admin_views_stats, name="admin_views_stats"),
    path("api/views-data/", views.api_views_data, name="api_views_data"),
    path("content-stats/<str:app_name>/", views.content_stats, name="content_stats"),
    path("api/content-data/<str:app_name>/", views.api_content_data, name="api_content_data"),
]