from django.shortcuts import render
from django.db.models import Count, Sum
from collector.models import CollectedData, CrawlLog
from sources.models import DataSource
from core.models import Category


def dashboard(request):
    """메인 대시보드"""
    # 최신 수집 데이터 (20개)
    latest_data = CollectedData.objects.select_related('source').all()[:20]

    # 통계
    total_data = CollectedData.objects.count()
    total_sources = DataSource.objects.filter(is_active=True).count()

    # 크롤링 통계
    crawl_stats = {
        'total': CrawlLog.objects.count(),
        'success': CrawlLog.objects.filter(status='success').count(),
        'failed': CrawlLog.objects.filter(status='failed').count(),
    }

    context = {
        'latest_data': latest_data,
        'total_data': total_data,
        'total_sources': total_sources,
        'crawl_stats': crawl_stats,
    }

    return render(request, 'core/dashboard.html', context)


def game_notices(request):
    """게임 공지사항 페이지"""
    # 메이플스토리 공지사항
    maple_notices = CollectedData.objects.filter(
        data__game='메이플스토리'
    ).select_related('source').order_by('-collected_at')[:50]

    context = {
        'notices': maple_notices,
        'game_name': '메이플스토리',
    }

    return render(request, 'core/game_notices.html', context)
