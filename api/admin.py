from django.contrib import admin
from .models import Game, GameCategory, Subscription, PushToken, UserProfile


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['game_id', 'display_name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['game_id', 'display_name']
    ordering = ['display_name']


@admin.register(GameCategory)
class GameCategoryAdmin(admin.ModelAdmin):
    list_display = ['game', 'name', 'created_at']
    list_filter = ['game', 'created_at']
    search_fields = ['game__display_name', 'name']
    ordering = ['game', 'name']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'game', 'category', 'created_at']
    list_filter = ['game', 'category', 'created_at']
    search_fields = ['user__username', 'game__display_name', 'category']
    ordering = ['-created_at']
    raw_id_fields = ['user']


@admin.register(PushToken)
class PushTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_type', 'token_preview', 'created_at']
    list_filter = ['device_type', 'created_at']
    search_fields = ['user__username', 'token']
    ordering = ['-created_at']
    raw_id_fields = ['user']

    def token_preview(self, obj):
        """토큰 미리보기 (앞 20자만)"""
        return f"{obj.token[:20]}..." if len(obj.token) > 20 else obj.token
    token_preview.short_description = '토큰'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'toss_user_key', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'toss_user_key']
    ordering = ['-created_at']
    raw_id_fields = ['user']
