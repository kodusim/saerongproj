from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Count, Sum, Q
from collector.models import CollectedData, CrawlLog
from sources.models import DataSource
from core.models import Category, SubCategory
from core import moscom_client
import logging

logger = logging.getLogger(__name__)


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


def mosquito_test(request):
    """모기 테스트 페이지 (세션 기반 로그인 보호)"""
    if request.session.get('mosquito_auth'):
        return render(request, 'core/mosquito_test.html')

    error = ''
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        if username == 'admin' and password == 'admin':
            request.session['mosquito_auth'] = True
            return render(request, 'core/mosquito_test.html')
        error = '아이디 또는 비밀번호가 올바르지 않습니다.'

    return render(request, 'core/mosquito_login.html', {'error': error})


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


def _require_mosquito_auth(request):
    """모기 대시보드 세션 인증 체크, 미인증 시 401 JsonResponse 반환"""
    if request.session.get('mosquito_auth'):
        return None
    return JsonResponse({'error': 'Unauthorized'}, status=401)


@require_GET
def moscom_devices(request):
    """MOSCOM API 장비 목록 프록시"""
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    try:
        force = request.GET.get('refresh') == '1'
        data = moscom_client.list_devices(force_refresh=force)
        return JsonResponse({'count': len(data), 'devices': data}, safe=False)
    except Exception as e:
        logger.exception('MOSCOM /device/listAll failed')
        return JsonResponse({'error': str(e)}, status=502)


@require_GET
def moscom_raw_collection(request):
    """MOSCOM API 기간별 포집 데이터 프록시
    쿼리스트링: start, end, device_uuid(선택)
    """
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    start = request.GET.get('start')
    end = request.GET.get('end')
    if not start or not end:
        return JsonResponse({'error': 'start, end query params required (ISO 8601)'}, status=400)
    try:
        data = moscom_client.raw_collection_bulk(
            start_dt=start,
            end_dt=end,
            device_uuid=request.GET.get('device_uuid') or None,
        )
        return JsonResponse({'data': data}, safe=False)
    except Exception as e:
        logger.exception('MOSCOM /device/rawCollectionBulk failed')
        return JsonResponse({'error': str(e)}, status=502)


@require_GET
def moscom_statistics(request):
    """MOSCOM API 장비별 일별 통계 프록시
    쿼리스트링: period(0=3개월, 1=4주, 2=7일, 3=기타, 기본=2), device_uuid(선택, 빈값=전체)
    """
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    try:
        period = request.GET.get('period', '2')
        device_uuid = request.GET.get('device_uuid', '')
        offset = int(request.GET.get('offset', '0'))
        data = moscom_client.get_statistics(
            device_uuid=device_uuid, period_type=period, offset=offset,
        )
        return JsonResponse({'count': len(data), 'stats': data}, safe=False)
    except Exception as e:
        logger.exception('MOSCOM /device/statistics failed')
        return JsonResponse({'error': str(e)}, status=502)


@require_GET
def moscom_daily(request):
    """MOSCOM API 일별 집계 프록시 — 7일 추세 탭용 (임의 기간)
    쿼리스트링: start, end (YYYY-MM-DD, KST). 최대 90일.
    """
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    from datetime import datetime, timedelta, timezone
    try:
        start_str = request.GET.get('start')
        end_str = request.GET.get('end')
        if not start_str or not end_str:
            return JsonResponse({'error': 'start, end query params required (YYYY-MM-DD)'}, status=400)
        try:
            start_d = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_d = datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'invalid date format, use YYYY-MM-DD'}, status=400)
        if end_d < start_d:
            start_d, end_d = end_d, start_d
        if (end_d - start_d).days > 90:
            return JsonResponse({'error': 'range too large (max 90 days)'}, status=400)

        # KST 00:00 → UTC-9h. end는 exclusive(다음날 00:00 KST)로 넓혀서 포함되도록.
        start_utc = datetime(start_d.year, start_d.month, start_d.day, 0, 0, 0, tzinfo=timezone.utc) - timedelta(hours=9)
        end_utc = datetime(end_d.year, end_d.month, end_d.day, 0, 0, 0, tzinfo=timezone.utc) + timedelta(days=1) - timedelta(hours=9)
        start_iso = start_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        end_iso = end_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        data = moscom_client.get_statistics_by_date(
            start_dt=start_iso, end_dt=end_iso, aggregation='day', device_uuid='0',
        )
        return JsonResponse({
            'count': len(data) if isinstance(data, list) else 0,
            'start': start_str, 'end': end_str,
            'data': data,
        }, safe=False)
    except Exception as e:
        logger.exception('MOSCOM /device/statisticsByDate (day) failed')
        return JsonResponse({'error': str(e)}, status=502)


@require_GET
def moscom_hourly(request):
    """MOSCOM API raw(시간별) 데이터 프록시 — 시간별 히트맵용
    쿼리스트링: start(ISO), end(ISO) (선택, 미지정 시 전날 00:00~다음날 06:00 UTC)
    """
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    from datetime import datetime, timedelta, timezone
    try:
        start = request.GET.get('start')
        end = request.GET.get('end')
        if not start or not end:
            # 기본: 최근 48시간치 (수집창 18:00~05:00 커버 가능)
            now = datetime.now(timezone.utc)
            end_dt = now
            start_dt = now - timedelta(days=2)
            start = start_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            end = end_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        data = moscom_client.get_statistics_by_date(
            start_dt=start, end_dt=end, aggregation='raw', device_uuid='0',
        )
        return JsonResponse({
            'count': len(data) if isinstance(data, list) else 0,
            'start': start, 'end': end,
            'data': data,
        }, safe=False)
    except Exception as e:
        logger.exception('MOSCOM /device/statisticsByDate failed')
        return JsonResponse({'error': str(e)}, status=502)
