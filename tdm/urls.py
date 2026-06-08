from django.urls import path
from . import views

urlpatterns = [
    path('', views.tdm_predict_page, name='tdm_predict_page'),
    path('login/', views.tdm_login, name='tdm_login'),
    path('logout/', views.tdm_logout, name='tdm_logout'),
    path('api/predict/', views.tdm_predict_api, name='tdm_predict_api'),
]
