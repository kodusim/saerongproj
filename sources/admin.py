from django.contrib import admin
from .models import DataSource


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'subcategory', 'crawler_type', 'crawl_interval',
                    'is_active', 'last_crawled_at']
    list_filter = ['subcategory__category', 'subcategory', 'crawler_type', 'is_active']
    search_fields = ['name', 'url']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['-created_at']
    readonly_fields = ['last_crawled_at', 'created_at', 'updated_at']

    fieldsets = (
        ('기본 정보', {
            'fields': ('subcategory', 'name', 'slug', 'url')
        }),
        ('크롤링 설정', {
            'fields': ('crawler_type', 'crawler_class', 'crawl_interval', 'config')
        }),
        ('상태', {
            'fields': ('is_active', 'last_crawled_at')
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
