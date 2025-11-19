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
    list_display = ['user', 'toss_user_key', 'created_at', 'has_premium']
    list_filter = ['created_at']
    search_fields = ['user__username', 'toss_user_key']
    ordering = ['-created_at']
    raw_id_fields = ['user']

    # 삭제 권한 제한 (슈퍼유저만 삭제 가능)
    def has_delete_permission(self, request, obj=None):
        # 테스트 계정만 삭제 가능하도록 제한 (선택사항)
        if obj and obj.user.is_superuser:
            return False  # 슈퍼유저 프로필은 삭제 불가
        return request.user.is_superuser

    def has_premium(self, obj):
        """프리미엄 구독 여부"""
        try:
            return '✅' if obj.user.premium_subscription.is_active() else '❌'
        except:
            return '❌'
    has_premium.short_description = '프리미엄'

    # 경고 메시지 추가
    def get_deleted_objects(self, objs, request):
        """삭제 확인 페이지에 경고 표시"""
        deleted_objects, model_count, perms_needed, protected = super().get_deleted_objects(objs, request)

        # 경고 메시지 추가
        warnings = [
            "⚠️ UserProfile 삭제 시 주의사항:",
            "- 해당 사용자는 재로그인 시 자동으로 Profile이 재생성됩니다",
            "- 구독 정보는 유지되지만 프리미엄 정보는 함께 삭제됩니다",
            "- 삭제 대신 User를 비활성화(is_active=False)하는 것을 권장합니다"
        ]

        return (warnings + list(deleted_objects), model_count, perms_needed, protected)
