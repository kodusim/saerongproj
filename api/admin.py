from django.contrib import admin
from django.utils.html import format_html
from django_summernote.admin import SummernoteModelAdmin
from .models import (
    Game, GameCategory, Subscription, PushToken, UserProfile,
    CarrotBalance, CarrotTransaction, IssueCategory, Issue
)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['game_id', 'display_name', 'icon_preview', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['game_id', 'display_name']
    ordering = ['display_name']
    fields = ['game_id', 'display_name', 'icon_image', 'icon_preview', 'icon_url', 'is_active']
    readonly_fields = ['icon_preview', 'created_at']

    def icon_preview(self, obj):
        """아이콘 미리보기"""
        if obj.icon_image:
            return f'<img src="{obj.icon_image.url}" width="50" height="50" style="border-radius: 8px;" />'
        return '이미지 없음'
    icon_preview.short_description = '아이콘'
    icon_preview.allow_tags = True


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
            return '✅' if obj.user.premium_subscription.is_active else '❌'
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


# ============================================
# 냉장고요리사 Admin
# ============================================

@admin.register(CarrotBalance)
class CarrotBalanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'updated_at', 'created_at']
    list_filter = ['updated_at', 'created_at']
    search_fields = ['user__username']
    ordering = ['-updated_at']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']

    # 관리자가 당근 지급/차감할 수 있도록
    actions = ['grant_carrots_100', 'grant_carrots_1000']

    def grant_carrots_100(self, request, queryset):
        for balance in queryset:
            balance.add_carrots(100, 'admin_grant')
        self.message_user(request, f"{queryset.count()}명에게 당근 100개를 지급했습니다.")
    grant_carrots_100.short_description = "선택된 사용자에게 당근 100개 지급"

    def grant_carrots_1000(self, request, queryset):
        for balance in queryset:
            balance.add_carrots(1000, 'admin_grant')
        self.message_user(request, f"{queryset.count()}명에게 당근 1000개를 지급했습니다.")
    grant_carrots_1000.short_description = "선택된 사용자에게 당근 1000개 지급"


@admin.register(CarrotTransaction)
class CarrotTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount_display', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user__username', 'order_id']
    ordering = ['-created_at']
    raw_id_fields = ['user']
    readonly_fields = ['user', 'transaction_type', 'amount', 'balance_after', 'order_id', 'created_at']

    def amount_display(self, obj):
        """변동량 표시 (색상으로 구분)"""
        if obj.amount > 0:
            return f'+{obj.amount}'
        return str(obj.amount)
    amount_display.short_description = '변동량'

    def has_add_permission(self, request):
        return False  # 직접 추가 불가

    def has_change_permission(self, request, obj=None):
        return False  # 수정 불가

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # 슈퍼유저만 삭제 가능


# ============================================
# 이슈모아 Admin (Summernote 에디터)
# ============================================

@admin.register(IssueCategory)
class IssueCategoryAdmin(admin.ModelAdmin):
    list_display = ['icon', 'name', 'category_id', 'order', 'is_active', 'issue_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'category_id']
    ordering = ['order', 'name']

    def issue_count(self, obj):
        """해당 카테고리의 이슈 수"""
        return obj.issues.count()
    issue_count.short_description = '이슈 수'


@admin.register(Issue)
class IssueAdmin(SummernoteModelAdmin):
    summernote_fields = ('content',)  # Summernote 에디터 적용 필드

    list_display = ['title', 'category', 'view_count', 'weekly_view_count', 'is_published', 'created_at']
    list_filter = ['category', 'is_published', 'created_at']
    list_editable = ['is_published']
    search_fields = ['title', 'content', 'preview']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('기본 정보', {
            'fields': ('category', 'title', 'is_published')
        }),
        ('내용', {
            'fields': ('content', 'preview'),
            'description': '미리보기는 비워두면 내용에서 자동 생성됩니다.'
        }),
        ('통계', {
            'fields': ('view_count', 'weekly_view_count'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ['view_count', 'weekly_view_count']

    # 주간 조회수 초기화 액션
    actions = ['reset_weekly_views']

    def reset_weekly_views(self, request, queryset):
        queryset.update(weekly_view_count=0)
        self.message_user(request, f"{queryset.count()}개 이슈의 주간 조회수를 초기화했습니다.")
    reset_weekly_views.short_description = "선택된 이슈의 주간 조회수 초기화"
