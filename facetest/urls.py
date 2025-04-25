from django.urls import path
from . import views

app_name = "facetest"

urlpatterns = [
    path('', views.index, name='index'),
]