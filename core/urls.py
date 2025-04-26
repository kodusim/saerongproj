from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.root, name="root"),
    path("inquiry/", views.inquiry, name="inquiry"),  # 새로운 URL 패턴 추가
]