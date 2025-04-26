from django.contrib import admin
from django.utils.html import format_html
from django_summernote.admin import SummernoteModelAdmin
from .models import BoardCategory, Post, Comment


class CommentInline(admin.TabularInline):
    """게시글 상세에서 댓글 인라인으로 표시"""
    model = Comment
    extra = 0
    fields = ('author', 'content', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(BoardCategory)
class BoardCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active', 'post_count', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    list_editable = ['order', 'is_active']
    
    def post_count(self, obj):
        return obj.posts.count()
    post_count.short_description = "게시글 수"


@admin.register(Post)
class PostAdmin(SummernoteModelAdmin):  # 변경: admin.ModelAdmin → SummernoteModelAdmin
    summernote_fields = ('content',)  # 추가: content 필드에 Summernote 적용
    list_display = ['title', 'category', 'author', 'view_count', 'comment_count', 'is_notice', 'image_preview', 'created_at']
    list_filter = ['category', 'is_notice', 'created_at']
    search_fields = ['title', 'content', 'author__username']
    readonly_fields = ['view_count', 'created_at', 'updated_at', 'image_preview_large']
    date_hierarchy = 'created_at'
    fieldsets = (
        (None, {
            'fields': ('category', 'title', 'content')
        }),
        ('작성 정보', {
            'fields': ('author', 'is_notice', 'view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('이미지', {
            'fields': ('image', 'image_preview_large'),
            'description': '게시글에 표시할 이미지를 업로드하세요. (선택사항)'
        }),
    )
    inlines = [CommentInline]
    
    def image_preview(self, obj):
        """이미지 미리보기 (목록용)"""
        if obj.image:
            return format_html('<img src="{}" height="50" />', obj.image.url)
        return "-"
    image_preview.short_description = "이미지"
    
    def image_preview_large(self, obj):
        """이미지 미리보기 (상세용)"""
        if obj.image:
            return format_html('<img src="{}" height="200" />', obj.image.url)
        return "이미지가 없습니다."
    image_preview_large.short_description = "이미지 미리보기"
    
    def comment_count(self, obj):
        return obj.comments.count()
    comment_count.short_description = "댓글 수"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['content_preview', 'post', 'author', 'created_at']
    list_filter = ['post__category', 'created_at']
    search_fields = ['content', 'author__username', 'post__title']
    readonly_fields = ['created_at', 'updated_at', 'post_link']
    
    def content_preview(self, obj):
        if len(obj.content) > 50:
            return obj.content[:50] + "..."
        return obj.content
    content_preview.short_description = "내용"
    
    def post_link(self, obj):
        url = obj.post.get_absolute_url()
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.post.title)
    post_link.short_description = "게시글 링크"