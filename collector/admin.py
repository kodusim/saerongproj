from django.contrib import admin
from .models import CollectedData, CrawlLog


@admin.register(CollectedData)
class CollectedDataAdmin(admin.ModelAdmin):
    list_display = ['source', 'collected_at', 'hash_key']
    list_filter = ['source__subcategory__category', 'source__subcategory', 'source', 'collected_at']
    search_fields = ['data', 'hash_key']
    readonly_fields = ['collected_at', 'hash_key']
    ordering = ['-collected_at']

    def has_add_permission(self, request):
        # 수집 데이터는 크롤러가 자동으로 추가하므로 수동 추가 불가
        return False


@admin.register(CrawlLog)
class CrawlLogAdmin(admin.ModelAdmin):
    list_display = ['source', 'status', 'items_collected', 'duration_seconds',
                    'started_at', 'completed_at']
    list_filter = ['status', 'source__subcategory__category', 'source', 'started_at']
    search_fields = ['error_message']
    readonly_fields = ['source', 'status', 'items_collected', 'error_message',
                      'started_at', 'completed_at', 'duration_seconds']
    ordering = ['-started_at']

    def has_add_permission(self, request):
        # 로그는 자동으로 생성되므로 수동 추가 불가
        return False

    def has_change_permission(self, request, obj=None):
        # 로그는 읽기 전용
        return False
