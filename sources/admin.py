from django.contrib import admin
from django import forms
from django.utils.html import format_html
from .models import DataSource


class DataSourceAdminForm(forms.ModelForm):
    """DataSource Admin 폼 - config 필드 도움말 추가"""

    class Meta:
        model = DataSource
        fields = '__all__'
        help_texts = {
            'crawler_class': format_html(
                '<br><strong>범용 크롤러 사용 예시:</strong><br>'
                '• <code>collector.crawlers.game_crawlers.GenericSeleniumCrawler</code> (JavaScript 필요한 사이트)<br>'
                '• <code>collector.crawlers.game_crawlers.GenericRequestsCrawler</code> (정적 HTML 사이트)<br>'
                '• <code>collector.crawlers.game_crawlers.MapleStoryCrawler</code> (메이플스토리 전용)'
            ),
            'config': format_html(
                '<br><strong>범용 크롤러(Generic) 사용 시 config 예시:</strong><br>'
                '<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">'
                '{{\n'
                '  "selectors": {{\n'
                '    "container": ".news_board ul li",\n'
                '    "title": "p a span",\n'
                '    "url": "p a",\n'
                '    "date": ".heart_date dd"\n'
                '  }},\n'
                '  "base_url": "https://maplestory.nexon.com",\n'
                '  "wait_selector": ".news_board",\n'
                '  "game_name": "메이플스토리",\n'
                '  "max_items": 20\n'
                '}}'
                '</pre>'
                '<strong>필수 항목:</strong> selectors.container, selectors.title, selectors.url<br>'
                '<strong>선택 항목:</strong> selectors.date, base_url, wait_selector, game_name, max_items'
            ),
        }


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    form = DataSourceAdminForm
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
            'fields': ('crawler_type', 'crawler_class', 'crawl_interval', 'config'),
            'description': '범용 크롤러를 사용하면 코드 수정 없이 config만으로 새 게임을 추가할 수 있습니다.'
        }),
        ('상태', {
            'fields': ('is_active', 'last_crawled_at')
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
