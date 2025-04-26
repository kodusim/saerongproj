from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html

# 관리자 사이트에 조회수 분석 메뉴 추가
class AnalyticsAdminSite(admin.AdminSite):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'analytics/views-stats/',
                self.admin_view(self.views_stats_view),
                name='admin_views_stats',
            ),
        ]
        return custom_urls + urls
    
    def views_stats_view(self, request):
        from .views import admin_views_stats
        return admin_views_stats(request)

    def each_context(self, request):
        context = super().each_context(request)
        context['analytics_url'] = reverse('admin:admin_views_stats')
        return context