from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib.admin.views.decorators import staff_member_required
from .models import BoardCategory, Post, Comment
from .forms import PostForm, CommentForm


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
    
    return render(request, 'community/post_detail.html', {
        'post': post, 
        'comments': comments,
        'comment_form': comment_form
    })


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
            post.save()
            messages.success(request, '게시글이 등록되었습니다.')
            return redirect('community:post_detail', post_id=post.id)
    else:
        form = PostForm()
    
    return render(request, 'community/post_form.html', {
        'form': form, 
        'category': category,
        'is_create': True
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
            # 관리자일 경우 작성자 변경 가능
            if request.user.is_staff and 'author' in request.POST:
                # 작성자 변경 시도
                try:
                    from accounts.models import User
                    author_id = request.POST.get('author')
                    if author_id:
                        new_author = User.objects.get(id=author_id)
                        post.author = new_author
                except Exception as e:
                    messages.error(request, f'작성자 변경 중 오류가 발생했습니다: {str(e)}')
            
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

@login_required
def post_like(request, post_id):
    """게시글 좋아요 토글"""
    post = get_object_or_404(Post, id=post_id)
    
    # 현재 사용자가 이미 좋아요를 눌렀는지 확인
    if request.user in post.likes.all():
        # 좋아요 취소
        post.likes.remove(request.user)
        liked = False
    else:
        # 좋아요 추가
        post.likes.add(request.user)
        liked = True
    
    # 비동기 요청인 경우 JSON 응답
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': post.likes.count()
        })
    
    # 일반 요청인 경우 이전 페이지로 리다이렉트
    return redirect(request.META.get('HTTP_REFERER', 'community:post_detail', args=[post_id]))