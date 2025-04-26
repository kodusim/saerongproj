from django.contrib import admin
from django.utils.html import format_html
from .models import Banner

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    """배너 관리자 설정"""
    list_display = ['title', 'banner_preview', 'url', 'is_active', 'order', 'created_at']
    list_editable = ['is_active', 'order']
    search_fields = ['title']
    list_filter = ['is_active']
    ordering = ['order', '-created_at']
    
    def banner_preview(self, obj):
        """배너 이미지 미리보기"""
        if obj.image:
            return format_html('<img src="{}" height="50" />', obj.image.url)
        return "이미지 없음"
    banner_preview.short_description = "미리보기"