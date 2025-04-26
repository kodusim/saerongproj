from django.db import models
from django.urls import reverse
from accounts.models import User


def post_image_upload_path(instance, filename):
    """게시글 이미지 업로드 경로"""
    import os
    import uuid
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('community/post_images', filename)


class BoardCategory(models.Model):
    """게시판 카테고리"""
    name = models.CharField("카테고리명", max_length=50)
    slug = models.SlugField("슬러그", unique=True, allow_unicode=True)
    description = models.TextField("설명", blank=True)
    order = models.PositiveIntegerField("순서", default=0)
    is_active = models.BooleanField("활성화", default=True)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "게시판 카테고리"
        verbose_name_plural = "게시판 카테고리"
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('community:category_detail', args=[self.slug])


class Post(models.Model):
    """게시글"""
    category = models.ForeignKey(BoardCategory, on_delete=models.CASCADE, related_name='posts', verbose_name="카테고리")
    title = models.CharField("제목", max_length=200)
    content = models.TextField("내용")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', verbose_name="작성자")
    view_count = models.PositiveIntegerField("조회수", default=0)
    is_notice = models.BooleanField("공지사항", default=False)
    created_at = models.DateTimeField("작성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)
    # 이미지 필드 추가
    image = models.ImageField("이미지", upload_to=post_image_upload_path, blank=True, null=True)
    # 좋아요 기능 추가
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True, verbose_name="좋아요")
    
    class Meta:
        ordering = ['-is_notice', '-created_at']
        verbose_name = "게시글"
        verbose_name_plural = "게시글"
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('community:post_detail', args=[self.id])
    
    def increase_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    @property
    def get_comment_count(self):
        """댓글 수 반환"""
        return self.comments.count() if hasattr(self, 'comments') else 0
    
    @property
    def like_count(self):
        """좋아요 수 반환"""
        return self.likes.count()


class Comment(models.Model):
    """댓글"""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name="게시글")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', verbose_name="작성자")
    content = models.TextField("내용")
    created_at = models.DateTimeField("작성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = "댓글"
        verbose_name_plural = "댓글"
    
    def __str__(self):
        return f"{self.author.username}의 댓글: {self.content[:20]}"