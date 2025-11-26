from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Sum, Q
from collector.models import CollectedData, CrawlLog
from sources.models import DataSource
from core.models import Category, SubCategory


def get_crawler_status():
    """크롤러 상태 정보 가져오기"""
    from saerong.celery import app as celery_app
    from datetime import datetime

    try:
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active() or {}
        reserved_tasks = inspect.reserved() or {}

        current_task = None
        is_running = False
        queue_length = 0
        queued_sources = []

        # 활성 태스크 확인
        for worker, tasks in active_tasks.items():
            for task in tasks:
                if task.get('name') == 'collector.tasks.crawl_data_source':
                    is_running = True
                    source_id = task['args'][0] if task.get('args') else None
                    time_start = task.get('time_start')

                    if source_id:
                        try:
                            source = DataSource.objects.select_related('subcategory').get(id=source_id)
                            current_task = {
                                'source_id': source_id,
                                'source_name': source.name,
                                'game_name': source.subcategory.name if source.subcategory else '',
                                'started_at': datetime.fromtimestamp(time_start) if time_start else None
                            }
                        except DataSource.DoesNotExist:
                            current_task = {
                                'source_id': source_id,
                                'source_name': '알 수 없음',
                                'game_name': '',
                                'started_at': datetime.fromtimestamp(time_start) if time_start else None
                            }
                    break

        # 대기 중인 태스크 확인
        for worker, tasks in reserved_tasks.items():
            for task in tasks:
                if task.get('name') == 'collector.tasks.crawl_data_source':
                    queue_length += 1
                    source_id = task['args'][0] if task.get('args') else None
                    if source_id:
                        try:
                            source = DataSource.objects.select_related('subcategory').get(id=source_id)
                            queued_sources.append({
                                'source_name': source.name,
                                'game_name': source.subcategory.name if source.subcategory else ''
                            })
                        except DataSource.DoesNotExist:
                            queued_sources.append({
                                'source_name': f'소스 #{source_id}',
                                'game_name': ''
                            })

        # 최근 크롤링 결과
        recent_logs = CrawlLog.objects.select_related('source', 'source__subcategory').order_by('-completed_at')[:5]
        last_crawl_results = []
        for log in recent_logs:
            last_crawl_results.append({
                'source_name': log.source.name if log.source else '알 수 없음',
                'game_name': log.source.subcategory.name if log.source and log.source.subcategory else '',
                'status': log.status,
                'items_collected': log.items_collected,
                'completed_at': log.completed_at,
                'duration_seconds': log.duration_seconds
            })

        return {
            'is_running': is_running,
            'current_task': current_task,
            'queue_length': queue_length,
            'queued_sources': queued_sources[:5],
            'total_sources': DataSource.objects.filter(is_active=True).count(),
            'last_crawl_results': last_crawl_results
        }

    except Exception as e:
        return {
            'is_running': False,
            'current_task': None,
            'queue_length': 0,
            'queued_sources': [],
            'total_sources': DataSource.objects.filter(is_active=True).count(),
            'last_crawl_results': [],
            'error': str(e)
        }


def dashboard(request):
    """메인 페이지 - 대분류 카테고리 표시"""
    categories = Category.objects.filter(is_active=True).order_by('order', 'name')

    # 크롤러 상태 정보 가져오기
    crawler_status = get_crawler_status()

    context = {
        'categories': categories,
        'crawler': crawler_status,
    }

    return render(request, 'core/home.html', context)


def category_detail(request, slug):
    """대분류 상세 - 중분류 목록 표시"""
    category = get_object_or_404(Category, slug=slug, is_active=True)

    # 검색어
    search_query = request.GET.get('search', '')

    # 중분류 목록 (활성 데이터 소스 개수 포함)
    subcategories = SubCategory.objects.filter(
        category=category,
        is_active=True
    ).annotate(
        active_sources_count=Count('data_sources', filter=Q(data_sources__is_active=True))
    ).order_by('order', 'name')

    # 검색 필터링
    if search_query:
        subcategories = subcategories.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    context = {
        'category': category,
        'subcategories': subcategories,
        'search_query': search_query,
    }

    return render(request, 'core/category_detail.html', context)


def subcategory_detail(request, slug):
    """중분류 상세 - 소분류별 데이터 표시 (탭 형식)"""
    subcategory = get_object_or_404(SubCategory, slug=slug, is_active=True)

    # 활성화된 데이터 소스들 가져오기
    data_sources = subcategory.data_sources.filter(is_active=True).order_by('name')

    # 각 데이터 소스별로 최신 10개 데이터 가져오기
    sources_with_data = []
    for source in data_sources:
        data_items = CollectedData.objects.filter(
            source=source
        ).order_by('-collected_at')[:10]

        sources_with_data.append({
            'source': source,
            'items': data_items
        })

    context = {
        'subcategory': subcategory,
        'category': subcategory.category,
        'sources_with_data': sources_with_data,
    }

    return render(request, 'core/subcategory_detail.html', context)


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
