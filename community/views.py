from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import BoardCategory, Post

def category_list(request):
    """게시판 카테고리 목록"""
    categories = BoardCategory.objects.filter(is_active=True)
    return render(request, 'community/category_list.html', {'categories': categories})

def post_list(request, category_slug):
    """카테고리별 게시글 목록"""
    category = get_object_or_404(BoardCategory, slug=category_slug, is_active=True)
    posts_list = Post.objects.filter(category=category)
    
    # 페이지네이션
    paginator = Paginator(posts_list, 15)  # 페이지당 15개 게시글
    page_number = request.GET.get('page', 1)
    posts = paginator.get_page(page_number)
    
    return render(request, 'community/post_list.html', {
        'category': category,
        'posts': posts,
    })

def post_detail(request, post_id):
    """게시글 상세"""
    post = get_object_or_404(Post, id=post_id)
    post.increase_view_count()  # 조회수 증가
    
    return render(request, 'community/post_detail.html', {'post': post})