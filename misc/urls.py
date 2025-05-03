from django.urls import path
from . import views

app_name = "misc"

urlpatterns = [
    path("", views.home, name="home"),
    path("fortune/", views.fortune_home, name="fortune_home"),
    path("fortune/<slug:slug>/", views.daily_fortune, name="daily_fortune"),
]