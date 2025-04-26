from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required
from . import views

app_name = "community"

urlpatterns = [
    # 카테고리 및 게시글 목록
    path('', views.category_list, name='category_list'),
    path('<slug:category_slug>/', views.post_list, name='category_detail'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    
    # 게시글 작성, 수정, 삭제
    path('<slug:category_slug>/create/', staff_member_required(views.post_create), name='post_create'),
    path('post/<int:post_id>/edit/', views.post_edit, name='post_edit'),
    path('post/<int:post_id>/delete/', views.post_delete, name='post_delete'),
    
    # 좋아요 기능
    path('post/<int:post_id>/like/', views.post_like, name='post_like'),
    
    # 댓글 관련
    path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
]