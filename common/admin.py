from django.contrib import admin
from .models import TossApp, AppUserToken


@admin.register(TossApp)
class TossAppAdmin(admin.ModelAdmin):
    list_display = ['app_id', 'display_name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['app_id', 'display_name']
    ordering = ['display_name']

    fieldsets = (
        ('기본 정보', {
            'fields': ('app_id', 'display_name', 'is_active')
        }),
        ('Toss API 설정', {
            'fields': ('toss_client_id', 'toss_decrypt_key', 'toss_decrypt_aad'),
            'classes': ('collapse',),
        }),
        ('mTLS 인증서', {
            'fields': ('cert_path', 'key_path'),
            'classes': ('collapse',),
        }),
        ('연결 끊기 콜백', {
            'fields': ('disconnect_callback_username', 'disconnect_callback_password'),
            'classes': ('collapse',),
        }),
    )


@admin.register(AppUserToken)
class AppUserTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'app', 'updated_at']
    list_filter = ['app']
    search_fields = ['user__username', 'app__display_name']
    ordering = ['-updated_at']
    readonly_fields = ['created_at', 'updated_at']
