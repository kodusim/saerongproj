from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from .models import BoardCategory, Post, Comment
from .forms import PostForm, CommentForm
from accounts.models import User
from functools import wraps
from django.core.exceptions import PermissionDenied

def category_list(request):
    """게시판 카테고리 목록과 각 카테고리별 최신 게시글 5개 표시"""
    # 모든 활성화된 카테고리 가져오기
    categories = BoardCategory.objects.filter(is_active=True)
    
    # 각 카테고리별 최신 게시글 5개씩 가져오기
    for category in categories:
        # 댓글 수를 계산하여 최신 게시글 5개 가져오기
        recent_posts = Post.objects.filter(category=category) \
                        .annotate(comment_count=Count('comments')) \
                        .order_by('-created_at')[:5]
        category.recent_posts = recent_posts
    
    return render(request, 'community/category_list.html', {'categories': categories})


def post_list(request, category_slug):
    """카테고리별 게시글 목록"""
    category = get_object_or_404(BoardCategory, slug=category_slug, is_active=True)
    
    # 검색 기능 구현
    search_query = request.GET.get('search', '')
    if search_query:
        posts_list = Post.objects.filter(
            Q(category=category) & 
            (Q(title__icontains=search_query) | Q(content__icontains=search_query))
        )
    else:
        posts_list = Post.objects.filter(category=category)
    
    # 댓글 수 미리 계산
    posts_list = posts_list.annotate(comment_count=Count('comments'))
    
    # 페이지네이션
    paginator = Paginator(posts_list, 15)  # 페이지당 15개 게시글
    page_number = request.GET.get('page', 1)
    posts = paginator.get_page(page_number)
    
    return render(request, 'community/post_list.html', {
        'category': category,
        'posts': posts,
        'search_query': search_query
    })


def post_detail(request, post_id):
    """게시글 상세"""
    post = get_object_or_404(Post, id=post_id)
    post.increase_view_count()  # 조회수 증가
    
    # 댓글 가져오기
    comments = post.comments.all()
    
    # 댓글 작성 폼
    comment_form = CommentForm()
    
    # 좋아요 상태 확인 (로그인한 경우)
    liked = False
    if request.user.is_authenticated:
        liked = post.likes.filter(id=request.user.id).exists()
    
    return render(request, 'community/post_detail.html', {
        'post': post, 
        'comments': comments,
        'comment_form': comment_form,
        'liked': liked
    })

def staff_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
@staff_member_required
def post_create(request, category_slug):
    """게시글 작성 - 관리자만 가능"""
    category = get_object_or_404(BoardCategory, slug=category_slug, is_active=True)
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.category = category
            post.author = request.user
            
            # 작성자 이름 변경 처리
            custom_author_name = request.POST.get('custom_author_name')
            if custom_author_name and custom_author_name != request.user.username:
                request.user.username = custom_author_name
                request.user.save()
            
            post.save()
            messages.success(request, '게시글이 등록되었습니다.')
            return redirect('community:post_detail', post_id=post.id)
    else:
        form = PostForm()
    
    return render(request, 'community/post_form.html', {
        'form': form, 
        'category': category,
        'is_create': True,
        'is_staff': request.user.is_staff
    })


@login_required
def post_edit(request, post_id):
    """게시글 수정"""
    post = get_object_or_404(Post, id=post_id)
    
    # 작성자나 관리자만 수정 가능
    if request.user != post.author and not request.user.is_staff:
        return HttpResponseForbidden("이 게시글을 수정할 권한이 없습니다.")
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            # 관리자일 경우 작성자 이름 변경 가능
            if request.user.is_staff:
                custom_author_name = request.POST.get('custom_author_name')
                if custom_author_name and custom_author_name != post.author.username:
                    post.author.username = custom_author_name
                    post.author.save()
            
            post = form.save()
            messages.success(request, '게시글이 수정되었습니다.')
            return redirect('community:post_detail', post_id=post.id)
    else:
        form = PostForm(instance=post)
    
    return render(request, 'community/post_form.html', {
        'form': form, 
        'post': post,
        'category': post.category,
        'is_create': False,
        'is_staff': request.user.is_staff
    })


@login_required
def post_delete(request, post_id):
    """게시글 삭제"""
    post = get_object_or_404(Post, id=post_id)
    
    # 작성자나 관리자만 삭제 가능
    if request.user != post.author and not request.user.is_staff:
        return HttpResponseForbidden("이 게시글을 삭제할 권한이 없습니다.")
    
    category = post.category
    post.delete()
    messages.success(request, '게시글이 삭제되었습니다.')
    return redirect('community:category_detail', category_slug=category.slug)


@login_required
@staff_member_required
def add_comment(request, post_id):
    """댓글 추가"""
    post = get_object_or_404(Post, id=post_id)
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            messages.success(request, '댓글이 등록되었습니다.')
    
    return redirect('community:post_detail', post_id=post.id)


@login_required
@staff_member_required
def delete_comment(request, comment_id):
    """댓글 삭제"""
    comment = get_object_or_404(Comment, id=comment_id)
    
    # 작성자나 관리자만 삭제 가능
    if request.user != comment.author and not request.user.is_staff:
        return HttpResponseForbidden("이 댓글을 삭제할 권한이 없습니다.")
    
    post_id = comment.post.id
    comment.delete()
    messages.success(request, '댓글이 삭제되었습니다.')
    return redirect('community:post_detail', post_id=post_id)


def post_like(request, post_id):
    """게시글 좋아요 토글 - 모든 사용자 가능"""
    post = get_object_or_404(Post, id=post_id)
    
    # IP 주소 확인
    client_ip = get_client_ip(request)
    
    # 세션에 좋아요 정보 저장
    liked_posts = request.session.get('liked_posts', {})
    post_id_str = str(post_id)
    
    # 좋아요 상태 확인 요청인 경우
    if request.method == 'GET' and request.GET.get('check') == 'true':
        liked = post_id_str in liked_posts
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': post.like_count
        })
    
    # 좋아요 토글
    if post_id_str in liked_posts:
        # 좋아요 취소
        del liked_posts[post_id_str]
        post.like_count = max(0, post.like_count - 1)  # 음수 방지
        liked = False
    else:
        # 좋아요 추가
        liked_posts[post_id_str] = True
        post.like_count = post.like_count + 1
        liked = True
    
    # 세션 업데이트
    request.session['liked_posts'] = liked_posts
    
    # 게시글 저장
    post.save(update_fields=['like_count'])
    
    # 비동기 요청인 경우 JSON 응답
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': post.like_count
        })
    
    # 일반 요청인 경우 이전 페이지로 리다이렉트
    return redirect('community:post_detail', post_id=post.id)

# IP 주소를 가져오는 헬퍼 함수
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip