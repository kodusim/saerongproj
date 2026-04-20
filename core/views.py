from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Count, Sum, Q
from collector.models import CollectedData, CrawlLog
from sources.models import DataSource
from core.models import Category, SubCategory
from core import moscom_client
from core import predictor
from core import user_store
from core import remedy_store
import logging
import json as _json

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
        is_admin = bool(request.session.get('mosquito_is_admin'))
        return render(request, 'core/mosquito_test.html', {
            'is_admin': is_admin,
            'login_id': request.session.get('mosquito_login_id', ''),
        })

    error = ''
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = user_store.authenticate(username, password)
        if user:
            request.session['mosquito_auth'] = True
            request.session['mosquito_is_admin'] = user['is_admin']
            request.session['mosquito_login_id'] = user['login_id']
            request.session['mosquito_allowed_devices'] = user['allowed_devices']
            return render(request, 'core/mosquito_test.html', {
                'is_admin': user['is_admin'],
                'login_id': user['login_id'],
            })
        error = '아이디 또는 비밀번호가 올바르지 않습니다.'

    return render(request, 'core/mosquito_login.html', {'error': error})


def mosquito_logout(request):
    """세션 로그아웃. GET/POST 모두 지원."""
    for k in ('mosquito_auth', 'mosquito_is_admin', 'mosquito_login_id', 'mosquito_allowed_devices'):
        if k in request.session:
            del request.session[k]
    from django.shortcuts import redirect
    return redirect('/mosquito-test/')


def _current_session_user(request):
    """세션에서 복원한 사용자. 없으면 None."""
    if not request.session.get('mosquito_auth'):
        return None
    return {
        'login_id': request.session.get('mosquito_login_id', ''),
        'is_admin': bool(request.session.get('mosquito_is_admin')),
        'allowed_devices': request.session.get('mosquito_allowed_devices'),
    }


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


def _require_admin(request):
    """admin 세션 체크"""
    if request.session.get('mosquito_auth') and request.session.get('mosquito_is_admin'):
        return None
    return JsonResponse({'error': 'Forbidden (admin only)'}, status=403)


@require_GET
def moscom_my_devices(request):
    """현재 로그인 사용자가 접근 가능한 장비 UUID 목록 반환.
    admin: is_admin=True + devices=null(전체 허용)
    user : 허용 UUID 배열
    """
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    su = _current_session_user(request)
    return JsonResponse({
        'login_id': su['login_id'],
        'is_admin': su['is_admin'],
        'allowed_devices': su['allowed_devices'],
    })


def moscom_users_api(request):
    """관리자 전용 사용자 CRUD.
    GET    /users/               → 목록
    POST   /users/               → 추가 (body: login_id, password, allowed_devices[])
    PUT    /users/<login_id>/    → 수정 (body: password? allowed_devices?)
    DELETE /users/<login_id>/    → 삭제
    """
    admin_err = _require_admin(request)
    if admin_err:
        return admin_err
    if request.method == 'GET':
        return JsonResponse({'users': user_store.list_users()})
    # 본문 파싱 (POST/PUT/DELETE)
    try:
        body = _json.loads((request.body or b'').decode('utf-8') or '{}')
    except _json.JSONDecodeError:
        body = {}
    if request.method == 'POST':
        try:
            user_store.create_user(
                login_id=body.get('login_id', ''),
                password=body.get('password', ''),
                allowed_devices=body.get('allowed_devices') or [],
            )
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        return JsonResponse({'ok': True, 'users': user_store.list_users()})
    return JsonResponse({'error': 'method not allowed'}, status=405)


def _visible_uuids_for(request):
    """세션 사용자의 허용 장비 UUID 집합. admin=None(=전부)."""
    su = _current_session_user(request)
    if not su:
        return set()
    if su.get('is_admin'):
        return None
    return set(su.get('allowed_devices') or [])


@require_GET
def moscom_remedy_methods(request):
    """방역 방법 6종 반환"""
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    return JsonResponse({'methods': remedy_store.list_methods()})


def moscom_remedy_api(request):
    """방역 계획 목록/추가
    GET  : 세션 사용자의 허용 장비 한정 목록
    POST : 새 계획 추가 (body: device_uuid, method_key, scheduled_date, note)
    """
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    visible = _visible_uuids_for(request)
    if request.method == 'GET':
        plans = remedy_store.list_plans(visible_uuids=visible)
        return JsonResponse({'plans': plans, 'methods': remedy_store.list_methods()})
    try:
        body = _json.loads((request.body or b'').decode('utf-8') or '{}')
    except _json.JSONDecodeError:
        body = {}
    if request.method == 'POST':
        dev_uuid = body.get('device_uuid')
        if visible is not None and dev_uuid not in visible:
            return JsonResponse({'error': '허용되지 않은 장비입니다'}, status=403)
        try:
            su = _current_session_user(request)
            plan = remedy_store.create_plan(
                owner_id=su.get('login_id', ''),
                device_uuid=dev_uuid,
                method_key=body.get('method_key'),
                scheduled_date=body.get('scheduled_date'),
                note=body.get('note', ''),
            )
            return JsonResponse({'ok': True, 'plan': plan})
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'method not allowed'}, status=405)


def moscom_remedy_detail_api(request, plan_id):
    """방역 계획 수정/삭제"""
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    plan = remedy_store.get_plan(plan_id)
    if not plan:
        return JsonResponse({'error': '해당 계획을 찾을 수 없습니다'}, status=404)
    visible = _visible_uuids_for(request)
    if visible is not None and plan.get('device_uuid') not in visible:
        return JsonResponse({'error': '권한 없음'}, status=403)
    try:
        body = _json.loads((request.body or b'').decode('utf-8') or '{}')
    except _json.JSONDecodeError:
        body = {}
    try:
        if request.method in ('PUT', 'PATCH'):
            # device_uuid 변경 시도 시 권한 재확인
            new_uuid = body.get('device_uuid')
            if new_uuid and visible is not None and new_uuid not in visible:
                return JsonResponse({'error': '허용되지 않은 장비입니다'}, status=403)
            p = remedy_store.update_plan(plan_id, body)
            return JsonResponse({'ok': True, 'plan': p})
        if request.method == 'DELETE':
            remedy_store.delete_plan(plan_id)
            return JsonResponse({'ok': True})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'method not allowed'}, status=405)


def moscom_user_detail_api(request, login_id):
    admin_err = _require_admin(request)
    if admin_err:
        return admin_err
    try:
        body = _json.loads((request.body or b'').decode('utf-8') or '{}')
    except _json.JSONDecodeError:
        body = {}
    try:
        if request.method in ('PUT', 'PATCH'):
            user_store.update_user(
                login_id=login_id,
                password=body.get('password') if body.get('password') else None,
                allowed_devices=body.get('allowed_devices') if 'allowed_devices' in body else None,
            )
            return JsonResponse({'ok': True, 'users': user_store.list_users()})
        if request.method == 'DELETE':
            user_store.delete_user(login_id)
            return JsonResponse({'ok': True, 'users': user_store.list_users()})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'method not allowed'}, status=405)


@require_GET
def moscom_devices(request):
    """MOSCOM API 장비 목록 프록시 (허용 장비만 반환)"""
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    try:
        force = request.GET.get('refresh') == '1'
        data = moscom_client.list_devices(force_refresh=force)
        # 관리자 세션일 때 '전체' 플래그로 원본 반환 (관리자 탭 사용자 추가에서 전 장비 리스트 필요)
        if request.GET.get('all') == '1' and bool(request.session.get('mosquito_is_admin')):
            return JsonResponse({'count': len(data), 'devices': data, 'admin_all': True}, safe=False)
        su = _current_session_user(request)
        filtered = user_store.filter_devices(su, data)
        return JsonResponse({'count': len(filtered), 'devices': filtered}, safe=False)
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


def _filter_records_by_uuid(request, records):
    """세션 사용자의 허용 장비로 레코드 배열 필터. admin은 그대로."""
    allowed = user_store.allowed_uuid_set(_current_session_user(request))
    if allowed is None:
        return records
    return [r for r in records if r.get('device_uuid') in allowed]


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
        data = _filter_records_by_uuid(request, data or [])
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
        data = _filter_records_by_uuid(request, data or [])
        return JsonResponse({
            'count': len(data) if isinstance(data, list) else 0,
            'start': start_str, 'end': end_str,
            'data': data,
        }, safe=False)
    except Exception as e:
        logger.exception('MOSCOM /device/statisticsByDate (day) failed')
        return JsonResponse({'error': str(e)}, status=502)


def _valid_kor(s):
    """한글/영문/숫자/공백만 포함한 정상 문자열인지 (깨진 주소 필터링)"""
    if not s or len(s) > 60:
        return False
    return any('\uac00' <= c <= '\ud7a3' or c.isalnum() or c == ' ' for c in s) and not any('\ud800' <= c <= '\udfff' or c == '\ufffd' for c in s)


@require_GET
def moscom_complaint_risk(request):
    """민원 가능 지역 위험 점수 산출 (4축 가중합)
    위험 점수: 절대 포집량 40% + 증가율 25% + 추세 20% + 전국 대비 15%
    민원 점수: 체감 포집량 35% + 급증 신호 25% + 야간 피크 25% + 주거지 인접 15%
    """
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    from datetime import datetime, timedelta, timezone
    from collections import defaultdict
    try:
        # 1) 장비 메타
        devices = moscom_client.list_devices()
        devices = user_store.filter_devices(_current_session_user(request), devices)
        meta = {}
        for d in devices:
            u = d.get('device_uuid')
            dv = d.get('device') or {}
            name = (dv.get('device_name') or '').strip() or u
            sido = (dv.get('address_sido') or '').strip()
            gungu = (dv.get('address_gungu') or '').strip()
            dong = (dv.get('address_dong') or '').strip()
            detail = (dv.get('address_detail') or '').strip()
            bad_min = ((dv.get('deviceSetting') or {}).get('bad_min')) or 100
            meta[u] = {
                'name': name,
                'sido': sido if _valid_kor(sido) else '',
                'gungu': gungu if _valid_kor(gungu) else '',
                'dong': dong if _valid_kor(dong) else '',
                'detail': detail if _valid_kor(detail) else '',
                'bad_min': bad_min,
            }

        # 2) 7일 통계 (장비별 일별 포집량)
        stats = moscom_client.get_statistics(device_uuid='', period_type='2', offset=0)
        daily = defaultdict(lambda: defaultdict(int))
        dates_set = set()
        for r in (stats or []):
            u = r.get('device_uuid')
            date = (r.get('created_date') or '')[:10]
            if not u or not date or u not in meta:
                continue
            daily[u][date] += (r.get('mosquito_count') or 0)
            dates_set.add(date)
        all_dates = sorted(dates_set)
        today = all_dates[-1] if all_dates else ''
        yday = all_dates[-2] if len(all_dates) >= 2 else ''
        week_dates = all_dates[-7:]

        # 3) 최근 48h raw 데이터 → 장비별 야간 피크 비율
        now = datetime.now(timezone.utc)
        start_iso = (now - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        end_iso = now.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        raw = moscom_client.get_statistics_by_date(start_dt=start_iso, end_dt=end_iso, aggregation='raw', device_uuid='0')
        per_dev_hour = defaultdict(lambda: [None] * 24)
        for r in (raw or []):
            u = r.get('device_uuid')
            if u not in meta:
                continue
            iso = r.get('created_date') or ''
            try:
                utc_h = int(iso[11:13])
            except Exception:
                continue
            kst_h = (utc_h + 9) % 24
            cnt = r.get('mosquito_count') or 0
            cur = per_dev_hour[u][kst_h]
            if cur is None or cnt > cur:
                per_dev_hour[u][kst_h] = cnt
        dev_night_ratio = {}
        for u, hr in per_dev_hour.items():
            deltas = [0] * 24
            prev = 0
            for h in range(24):
                v = hr[h]
                if v is None:
                    continue
                d = v - prev
                deltas[h] = d if d > 0 else 0
                prev = v
            night = sum(deltas[19:24])
            total = sum(deltas)
            dev_night_ratio[u] = (night / total) if total > 0 else 0.0

        # 4) 오늘 백분위
        today_counts = sorted([daily[u].get(today, 0) for u in meta.keys()], reverse=True)
        n = len(today_counts)
        def percentile_rank(v):
            if n <= 1:
                return 100
            above = sum(1 for x in today_counts if x < v)
            return round((above / (n - 1)) * 100)

        # 5) 주거지 키워드
        residential_keywords = ['공원', '아파트', '주거', '학교', '초등', '중학', '고등', '어린이집', '유치원']
        def residential_hit(m):
            txt = ' '.join([m['sido'], m['gungu'], m['dong'], m['detail'], m['name']])
            return any(k in txt for k in residential_keywords)

        # 6) 장비별 점수 계산
        results = []
        for u, m in meta.items():
            today_cnt = daily[u].get(today, 0) if today else 0
            yday_cnt = daily[u].get(yday, 0) if yday else 0
            week_vals = [daily[u].get(d, 0) for d in week_dates]
            week_avg = sum(week_vals) / len(week_vals) if week_vals else 0

            axis1 = min(100, (today_cnt / m['bad_min']) * 100) if m['bad_min'] > 0 else 0
            if yday_cnt > 0:
                axis2 = max(0, min(100, (today_cnt - yday_cnt) / yday_cnt * 100))
            else:
                axis2 = 50 if today_cnt > 0 else 0
            if len(week_vals) >= 4:
                half = len(week_vals) // 2
                fh = sum(week_vals[:half]) / half if half > 0 else 0
                lh = sum(week_vals[half:]) / (len(week_vals) - half)
                if fh > 0:
                    tr = (lh - fh) / fh * 100
                    axis3 = max(0, min(100, (tr / 30) * 100))
                else:
                    axis3 = 50 if lh > 0 else 0
            else:
                axis3 = 0
            axis4 = percentile_rank(today_cnt)

            risk_score = round(axis1 * 0.40 + axis2 * 0.25 + axis3 * 0.20 + axis4 * 0.15, 1)
            if risk_score <= 20: risk_level = '안전'
            elif risk_score <= 40: risk_level = '관심'
            elif risk_score <= 60: risk_level = '주의'
            elif risk_score <= 80: risk_level = '경고'
            else: risk_level = '심각'

            night_ratio = dev_night_ratio.get(u, 0.0)
            axis_felt = axis1
            axis_surge = axis2
            axis_night = min(100, (night_ratio / 0.6) * 100) if night_ratio else 0
            resi_hit = residential_hit(m)
            axis_resi = 80 if resi_hit else 20

            complaint_score = round(
                axis_felt * 0.35 + axis_surge * 0.25 + axis_night * 0.25 + axis_resi * 0.15, 1
            )
            if complaint_score <= 30: complaint_level = '낮음'
            elif complaint_score <= 60: complaint_level = '보통'
            else: complaint_level = '높음'

            # 주요 원인 (민원 기여도 상위 2개)
            axes_complaint = [
                ('체감 포집량', axis_felt, f'기준치(bad_min {m["bad_min"]}) 대비 {round(today_cnt / max(m["bad_min"],1) * 100)}%'),
                ('급증 신호', axis_surge, f'어제 {yday_cnt}마리 → 오늘 {today_cnt}마리'),
                ('야간 피크', axis_night, f'19~23시 비중 {round(night_ratio*100)}%'),
                ('주거지 인접', axis_resi, '주거지 키워드 매칭' if resi_hit else '주거지 키워드 없음'),
            ]
            axes_complaint.sort(key=lambda x: x[1], reverse=True)
            causes = [{'name': a[0], 'score': round(a[1], 1), 'detail': a[2]} for a in axes_complaint[:2]]

            actions = []
            if complaint_score >= 61:
                actions.append('긴급 유충 방제 + 주민 사전 안내문 배포')
            if risk_score >= 61 and axis3 >= 60:
                actions.append('성충 방제 + 24시간 모니터링')
            if axis_night >= 60:
                actions.append('19~23시 집중 방제')
            if not actions:
                actions.append('정기 예찰 유지')

            region = ' '.join(p for p in [m['sido'], m['gungu']] if p) or '기타'

            results.append({
                'uuid': u,
                'name': m['name'],
                'region': region,
                'address': ' '.join(p for p in [m['gungu'], m['dong'], m['detail']] if p),
                'bad_min': m['bad_min'],
                'today_count': today_cnt,
                'yday_count': yday_cnt,
                'week_avg': round(week_avg, 1),
                'night_ratio': round(night_ratio, 3),
                'residential': resi_hit,
                'risk': {
                    'score': risk_score, 'level': risk_level,
                    'axes': {
                        '절대 포집량': round(axis1, 1),
                        '증가율': round(axis2, 1),
                        '추세': round(axis3, 1),
                        '전국 대비': round(axis4, 1),
                    },
                },
                'complaint': {
                    'score': complaint_score, 'level': complaint_level,
                    'axes': {
                        '체감 포집량': round(axis_felt, 1),
                        '급증 신호': round(axis_surge, 1),
                        '야간 피크': round(axis_night, 1),
                        '주거지 인접': round(axis_resi, 1),
                    },
                },
                'causes': causes,
                'actions': actions,
            })

        results.sort(key=lambda r: (r['complaint']['score'], r['risk']['score']), reverse=True)

        return JsonResponse({
            'count': len(results),
            'today': today,
            'criteria': {
                'risk': {
                    'weights': {'절대 포집량': 40, '증가율': 25, '추세': 20, '전국 대비': 15},
                    'levels': {'안전': '0~20', '관심': '21~40', '주의': '41~60', '경고': '61~80', '심각': '81~100'},
                },
                'complaint': {
                    'weights': {'체감 포집량': 35, '급증 신호': 25, '야간 피크': 25, '주거지 인접': 15},
                    'levels': {'낮음': '0~30', '보통': '31~60', '높음': '61~100'},
                    'residential_keywords': residential_keywords,
                },
            },
            'items': results,
        }, safe=False)
    except Exception as e:
        logger.exception('complaint_risk failed')
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def moscom_predict(request):
    """AI 모기 발생 예측 (내일~3일 후, 장비 52개 전체)
    학습 데이터: 청주 3개소·여름 2개월. 다른 지역/계절은 참고값.
    """
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    from datetime import datetime, timedelta, timezone
    try:
        # 최근 10일 일별 통계 (lag7까지 쓰니 넉넉하게)
        today_kst = datetime.now(timezone(timedelta(hours=9))).date()
        start_d = today_kst - timedelta(days=10)
        start_iso = datetime(start_d.year, start_d.month, start_d.day, 0, 0, 0, tzinfo=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        end_iso = (datetime(today_kst.year, today_kst.month, today_kst.day, 0, 0, 0, tzinfo=timezone.utc) + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.000Z')

        daily = moscom_client.get_statistics_by_date(start_dt=start_iso, end_dt=end_iso, aggregation='day', device_uuid='0')
        devices = moscom_client.list_devices()
        # 세션 사용자 허용 장비로 제한
        devices = user_store.filter_devices(_current_session_user(request), devices)

        # 장비 메타
        meta = {}
        for d in devices:
            u = d.get('device_uuid')
            dv = d.get('device') or {}
            name = (dv.get('device_name') or '').strip() or u
            parts = [dv.get('address_sido'), dv.get('address_gungu')]
            region = ' '.join(p for p in parts if p and len(p) < 40 and any(ord(c) < 0x3400 or 0xAC00 <= ord(c) <= 0xD7A3 for c in p)) or '기타'
            meta[u] = {'name': name, 'region': region}

        # 장비별 history 생성
        hist_by_uuid = {u: [] for u in meta}
        for r in (daily or []):
            u = r.get('device_uuid')
            if u not in hist_by_uuid:
                continue
            date = (r.get('created_date') or '')[:10]
            if date:
                hist_by_uuid[u].append({'date': date, 'count': r.get('mosquito_count') or 0})

        # 예측 대상 입력
        inputs = []
        for u, m in meta.items():
            inputs.append({
                'uuid': u,
                'name': m['name'],
                'region': m['region'],
                'history': hist_by_uuid[u],
            })

        try:
            days_ahead = int(request.GET.get('days', '3'))
        except (TypeError, ValueError):
            days_ahead = 3
        preds = predictor.predict_for_devices(inputs, days_ahead=days_ahead)

        # 방역 계획 효과 반영 (post-processing)
        def _grade(n):
            if n <= 10: return '안전'
            if n <= 50: return '관심'
            if n <= 100: return '주의'
            if n <= 200: return '경고'
            return '위험'
        remedy_summary_by_uuid = {}
        for p in preds:
            uid = p['uuid']
            new_preds = []
            applied_by_date = {}
            for pp in p['predictions']:
                factor, applied = remedy_store.adjustment_factor(uid, pp.get('date'))
                orig = pp.get('predicted') or 0
                adj = int(round(orig * factor))
                new_preds.append({
                    'date': pp['date'],
                    'predicted': adj,
                    'predicted_raw': orig,
                    'remedy_factor': round(factor, 3),
                })
                if applied:
                    applied_by_date[pp['date']] = applied
            p['predictions'] = new_preds
            ps = [x['predicted'] for x in new_preds]
            p['max_predicted'] = max(ps) if ps else 0
            p['avg_predicted'] = round(sum(ps) / len(ps)) if ps else 0
            p['grade'] = _grade(p['max_predicted'])
            if applied_by_date:
                p['remedy_applied'] = applied_by_date
                remedy_summary_by_uuid[uid] = applied_by_date

        # max_predicted 내림차순 정렬
        preds.sort(key=lambda x: x.get('max_predicted', 0), reverse=True)
        return JsonResponse({
            'count': len(preds),
            'model': 'RandomForest',
            'remedy_applied_count': len(remedy_summary_by_uuid),
            'model_info': {
                'name': 'MOSCOM AI v1.0',
                'algorithm': 'Random Forest Regressor',
                'n_trees': 200, 'max_depth': 10,
                'trained_on': '청주 흥덕구 3개소 · 2025년 7~8월 · 187건',
                'features': 34,
            },
            'disclaimer': '학습 데이터: 청주 3개소·2025년 7~8월. 다른 지역/계절은 참고값.',
            'predictions': preds,
        }, safe=False)
    except Exception as e:
        logger.exception('AI predict failed')
        return JsonResponse({'error': str(e)}, status=500)


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
        data = _filter_records_by_uuid(request, data or [])
        return JsonResponse({
            'count': len(data) if isinstance(data, list) else 0,
            'start': start, 'end': end,
            'data': data,
        }, safe=False)
    except Exception as e:
        logger.exception('MOSCOM /device/statisticsByDate failed')
        return JsonResponse({'error': str(e)}, status=502)
