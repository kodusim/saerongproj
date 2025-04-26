from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, Profile


class ProfileInline(admin.StackedInline):
    """User Admin에서 프로필을 인라인으로 관리"""
    model = Profile
    can_delete = False
    verbose_name_plural = '프로필'
    readonly_fields = ['avatar_preview']
    
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" height="150" />', obj.avatar.url)
        return "프로필 이미지 없음"
    avatar_preview.short_description = "프로필 이미지 미리보기"


class CustomUserAdmin(UserAdmin):
    """확장된 User 관리자"""
    inlines = [ProfileInline]
    list_display = UserAdmin.list_display + ('avatar_thumbnail',)
    
    def avatar_thumbnail(self, obj):
        try:
            if obj.profile and obj.profile.avatar:
                return format_html('<img src="{}" height="30" style="border-radius: 50%;" />', obj.profile.avatar.url)
            else:
                return format_html('<div style="width: 30px; height: 30px; background-color: #e9ecef; border-radius: 50%; display: flex; align-items: center; justify-content: center;">{}</div>', obj.username[0].upper())
        except:
            return "-"
    avatar_thumbnail.short_description = "프로필"


# User 모델 등록
admin.site.register(User, CustomUserAdmin)

# 직접 Profile 모델을 관리자에 등록하지 않습니다 (User를 통해 관리)