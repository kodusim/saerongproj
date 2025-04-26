from django.contrib import admin
from django.utils.translation import gettext_lazy as _

class AnalyticsAdminSite:
    """
    관리자 사이트에 '조회수 분석' 메뉴를 추가하는 믹스인
    기존 admin 사이트를 확장하는 방식으로 변경
    """
    
    def add_analytics_menu():
        """Django 관리자 사이트에 조회수 분석 메뉴 추가"""
        # 기존 admin 인스턴스 가져오기
        _admin_site = admin.site
        
        # 기존 get_app_list 메서드 저장
        original_get_app_list = _admin_site.get_app_list
        
        def custom_get_app_list(request):
            # 원래 앱 목록 가져오기
            app_list = original_get_app_list(request)
            
            # '사이트 관리' 앱이 이미 있는지 확인
            site_admin_app = None
            for app in app_list:
                if app.get('app_label') == 'analytics':
                    site_admin_app = app
                    break
            
            # 없으면 새로 생성
            if site_admin_app is None:
                site_admin_app = {
                    'name': _('사이트 관리'),
                    'app_label': 'analytics',
                    'app_url': '#',
                    'has_module_perms': True,
                    'models': [],
                }
                app_list.append(site_admin_app)
            
            # 조회수 분석 메뉴 추가
            site_admin_app['models'].append({
                'name': _('조회수 분석'),
                'object_name': 'ViewsStats',
                'admin_url': '/analytics/views-stats/',  # 여기를 수정: /admin/analytics/views-stats/ -> /analytics/views-stats/
                'view_only': True,
                'perms': {'view': True}
            })
            
            return app_list
        
        # admin 사이트의 get_app_list 메서드 대체
        _admin_site.get_app_list = custom_get_app_list