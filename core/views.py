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
from core import report_store
from core import kakao_client
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
        body = _json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
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


def _build_overview_data(su):
    """종합 현황 탭 + 보고서 재사용용 데이터 빌더.
    허용 장비(su 기준)로만 산출.
    """
    from datetime import datetime, timedelta, timezone
    from collections import defaultdict

    devices = moscom_client.list_devices()
    devices = user_store.filter_devices(su, devices)
    allowed_uuids = {d.get('device_uuid') for d in devices}

    # 이름/주소 맵
    meta = {}
    for d in devices:
        dv = d.get('device') or {}
        nm = (dv.get('device_name') or '').strip() or d.get('device_uuid')
        addr = ' '.join(p for p in [dv.get('address_gungu'), dv.get('address_dong')] if p and len(p) < 40 and _valid_kor(p)) or ''
        meta[d.get('device_uuid')] = {
            'name': nm, 'addr': addr,
            'bad_min': ((dv.get('deviceSetting') or {}).get('bad_min')) or 100,
            'battery': dv.get('battery') or 0,
            'fan': dv.get('fan') or 0,
            'updated_date': dv.get('updated_date'),
        }

    # 7일 통계 (허용 장비만)
    stats = moscom_client.get_statistics(device_uuid='', period_type='2', offset=0)
    stats = [r for r in (stats or []) if r.get('device_uuid') in allowed_uuids]

    daily = defaultdict(lambda: defaultdict(int))
    dates_set = set()
    for r in stats:
        u = r.get('device_uuid'); dd = (r.get('created_date') or '')[:10]
        if u and dd:
            daily[u][dd] += (r.get('mosquito_count') or 0)
            dates_set.add(dd)
    sorted_dates = sorted(dates_set)
    today_d = sorted_dates[-1] if sorted_dates else ''
    yday_d = sorted_dates[-2] if len(sorted_dates) >= 2 else ''

    # 오늘 값
    today_by_dev = {u: daily[u].get(today_d, 0) for u in allowed_uuids} if today_d else {u: 0 for u in allowed_uuids}
    today_total = sum(today_by_dev.values())
    yday_total = sum(daily[u].get(yday_d, 0) for u in allowed_uuids) if yday_d else 0
    change_pct = round((today_total - yday_total) / yday_total * 100) if yday_total else 0

    # 최다 포집 장비
    top_dev = None
    if today_by_dev:
        top_uuid, top_count = max(today_by_dev.items(), key=lambda x: x[1])
        top_dev = {
            'uuid': top_uuid,
            'name': meta.get(top_uuid, {}).get('name', top_uuid),
            'addr': meta.get(top_uuid, {}).get('addr', ''),
            'count': top_count,
        }

    # 장비별 7일 평균 + 추세 + 위험점수 (complaint-risk 축약본)
    warn_count = 0         # 위험 점수 61+ (경고/심각)
    anomaly_today = 0      # 오늘 bad_min 초과
    complaint_high = 0     # 민원 위험 61+
    now_utc = datetime.now(timezone.utc)
    offline_count = 0
    check_count = 0
    trust_scores = []
    low_batt_count = 0

    # 장비별 위험·민원 축약 계산
    # 야간 피크 계산 위해 raw 가져옴 (48h)
    start_iso = (now_utc - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    end_iso = now_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    try:
        raw = moscom_client.get_statistics_by_date(start_dt=start_iso, end_dt=end_iso, aggregation='raw', device_uuid='0')
    except Exception:
        raw = []
    raw = [r for r in (raw or []) if r.get('device_uuid') in allowed_uuids]
    per_dev_hour = defaultdict(lambda: [None] * 24)
    for r in raw:
        u = r.get('device_uuid')
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
        prev = 0; deltas = [0] * 24
        for h in range(24):
            v = hr[h]
            if v is None: continue
            d_ = v - prev; deltas[h] = d_ if d_ > 0 else 0; prev = v
        total = sum(deltas); night = sum(deltas[19:24])
        dev_night_ratio[u] = (night / total) if total > 0 else 0.0

    # 오늘 백분위 계산용
    today_counts_sorted = sorted(today_by_dev.values(), reverse=True)
    n = len(today_counts_sorted)

    def percentile_rank(v):
        if n <= 1: return 100
        above = sum(1 for x in today_counts_sorted if x < v)
        return round((above / (n - 1)) * 100)

    residential_keywords = ['공원', '아파트', '주거', '학교', '초등', '중학', '고등', '어린이집', '유치원']

    def is_resi(m):
        txt = ' '.join([m.get('addr') or '', m.get('name') or ''])
        return any(k in txt for k in residential_keywords)

    # 장비별 상세 계산
    device_rows = []
    for u in allowed_uuids:
        m = meta.get(u, {})
        today_c = today_by_dev.get(u, 0)
        yday_c = daily[u].get(yday_d, 0) if yday_d else 0
        week_vals = [daily[u].get(d, 0) for d in sorted_dates[-7:]]
        week_avg = sum(week_vals) / len(week_vals) if week_vals else 0

        # 위험 점수 4축
        ax1 = min(100, (today_c / m.get('bad_min', 100)) * 100) if m.get('bad_min', 0) > 0 else 0
        ax2 = max(0, min(100, (today_c - yday_c) / yday_c * 100)) if yday_c > 0 else (50 if today_c > 0 else 0)
        if len(week_vals) >= 4:
            half = len(week_vals) // 2
            fh = sum(week_vals[:half]) / half if half > 0 else 0
            lh = sum(week_vals[half:]) / (len(week_vals) - half)
            ax3 = max(0, min(100, ((lh - fh) / fh * 100) / 30 * 100)) if fh > 0 else (50 if lh > 0 else 0)
        else:
            ax3 = 0
        ax4 = percentile_rank(today_c)
        risk_score = round(ax1 * 0.40 + ax2 * 0.25 + ax3 * 0.20 + ax4 * 0.15, 1)
        if risk_score <= 20: risk_lv = '안전'
        elif risk_score <= 40: risk_lv = '관심'
        elif risk_score <= 60: risk_lv = '주의'
        elif risk_score <= 80: risk_lv = '경고'
        else: risk_lv = '심각'
        if risk_score >= 61: warn_count += 1
        if today_c >= m.get('bad_min', 100) and m.get('bad_min', 0) > 0: anomaly_today += 1

        # 민원 점수
        night_ratio = dev_night_ratio.get(u, 0.0)
        ax_night = min(100, (night_ratio / 0.6) * 100) if night_ratio else 0
        ax_resi = 80 if is_resi(m) else 20
        complaint_score = round(ax1 * 0.35 + ax2 * 0.25 + ax_night * 0.25 + ax_resi * 0.15, 1)
        if complaint_score <= 30: cp_lv = '낮음'
        elif complaint_score <= 60: cp_lv = '보통'
        else: cp_lv = '높음'
        if complaint_score >= 61: complaint_high += 1

        # 장비 신뢰도 (equipment-health 축약)
        battery = m.get('battery', 0)
        fan = m.get('fan', 0)
        if battery < 15: low_batt_count += 1
        ax_bat = 100 if battery >= 50 else 80 if battery >= 30 else 60 if battery >= 20 else 35 if battery >= 10 else 10
        ax_fan = 100 if fan == 1 else 30
        try:
            ud = m.get('updated_date') or ''
            udt = datetime.fromisoformat(ud.replace('Z', '+00:00'))
            delay_min = (now_utc - udt).total_seconds() / 60
        except Exception:
            delay_min = 99999
        if delay_min <= 120: ax_sig = 100
        elif delay_min <= 360: ax_sig = 80
        elif delay_min <= 720: ax_sig = 55
        elif delay_min <= 1440: ax_sig = 30
        else: ax_sig = 5
        zero_total_3 = sum(week_vals[-3:]) if week_vals else 0
        ax_zero = 40 if (len(week_vals) >= 3 and zero_total_3 == 0) else (65 if zero_total_3 == 0 else 100)
        trust_score = round(ax_bat * 0.25 + ax_fan * 0.20 + ax_sig * 0.35 + ax_zero * 0.20, 1)
        trust_scores.append(trust_score)

        if ax_sig <= 30: equip_status = '오프라인'; offline_count += 1
        elif trust_score < 60 or battery < 15 or (fan == 0 and ax_sig >= 55): equip_status = '점검필요'; check_count += 1
        else: equip_status = '정상'

        # 추세 방향
        if len(week_vals) >= 3:
            tr = week_vals[-1] - (sum(week_vals[:-1]) / len(week_vals[:-1]))
            trend_dir = '↑' if tr > 3 else '↓' if tr < -3 else '→'
        else:
            trend_dir = '·'

        device_rows.append({
            'uuid': u, 'name': m.get('name'), 'addr': m.get('addr'),
            'today': today_c, 'yday': yday_c, 'week_avg': round(week_avg, 1),
            'risk_score': risk_score, 'risk_level': risk_lv,
            'complaint_score': complaint_score, 'complaint_level': cp_lv,
            'trust_score': trust_score, 'status': equip_status,
            'battery': battery, 'trend': trend_dir,
            'bad_min': m.get('bad_min', 100),
        })

    # 포집량 내림차순 정렬
    device_rows.sort(key=lambda r: r['today'], reverse=True)

    avg_trust = round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 0

    return {
        'today': today_d,
        'yday': yday_d,
        'kpi': {
            'today_total': today_total,
            'yday_total': yday_total,
            'change_pct': change_pct,
            'top_dev': top_dev,
            'warn_count': warn_count,
            'anomaly_today': anomaly_today,
            'complaint_high': complaint_high,
            'equip_bad': offline_count + check_count,
            'offline_count': offline_count,
            'check_count': check_count,
            'low_batt_count': low_batt_count,
            'avg_trust': avg_trust,
            'total_devices': len(allowed_uuids),
        },
        'devices': device_rows,
    }


@require_GET
def moscom_overview(request):
    """종합 현황 탭용 집계 API. 허용 장비 기준."""
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    su = _current_session_user(request)
    try:
        data = _build_overview_data(su)
        return JsonResponse(data)
    except Exception as e:
        logger.exception('overview failed')
        return JsonResponse({'error': str(e)}, status=500)


def _build_report_body(period, base_date, su, request):
    """보고서 본문(GPT) + 요약 데이터 구성. (report_text, summary, scoped_uuids, source, payload_summary)"""
    from datetime import datetime, timedelta, timezone
    from collections import defaultdict
    from django.conf import settings as dj_settings

    start_s, end_s = report_store.period_range(period, base_date)

    devices = moscom_client.list_devices()
    devices = user_store.filter_devices(su, devices)
    allowed_uuids = [d.get('device_uuid') for d in devices]

    # 일별 집계 (기간 범위)
    start_iso = datetime.strptime(start_s, '%Y-%m-%d').strftime('%Y-%m-%dT00:00:00.000Z')
    end_iso = (datetime.strptime(end_s, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z')
    daily_records = moscom_client.get_statistics_by_date(
        start_dt=start_iso, end_dt=end_iso, aggregation='day', device_uuid='0'
    )
    allowed_set = set(allowed_uuids)
    daily_records = [r for r in (daily_records or []) if r.get('device_uuid') in allowed_set]

    daily = defaultdict(lambda: defaultdict(int))
    for r in daily_records:
        u = r.get('device_uuid')
        d = (r.get('created_date') or '')[:10]
        if u and d:
            daily[u][d] += (r.get('mosquito_count') or 0)

    # 날짜 배열
    dates_in_range = sorted({(r.get('created_date') or '')[:10] for r in daily_records if r.get('created_date')})
    total_in_period = sum(sum(v.values()) for v in daily.values())
    # 일평균
    n_days = max(1, len(dates_in_range))
    avg_per_day = round(total_in_period / n_days, 1)

    # 장비 이름 매핑
    name_map = {}
    for d in devices:
        dv = d.get('device') or {}
        nm = (dv.get('device_name') or '').strip() or d.get('device_uuid')
        addr = ' '.join(p for p in [dv.get('address_gungu'), dv.get('address_dong')] if p and len(p) < 40) or ''
        name_map[d.get('device_uuid')] = {
            'name': nm, 'addr': addr,
            'bad_min': ((dv.get('deviceSetting') or {}).get('bad_min')) or 100,
        }

    # 장비별 기간 합계 Top 5
    dev_totals = sorted(
        [(u, sum(daily[u].values())) for u in daily.keys()],
        key=lambda x: x[1], reverse=True
    )[:5]

    # 이상 감지 (기간 중 어느 하루라도 bad_min 초과)
    anomalies = []
    for u in allowed_uuids:
        bm = name_map.get(u, {}).get('bad_min', 100)
        for d, c in daily[u].items():
            if c >= bm and bm > 0:
                anomalies.append({
                    'name': name_map[u]['name'],
                    'addr': name_map[u]['addr'],
                    'date': d, 'count': c, 'bad_min': bm,
                })
    anomalies.sort(key=lambda a: a['count'], reverse=True)
    anomalies = anomalies[:10]

    # 방역 계획 (해당 기간 겹치는 것)
    visible = allowed_set if not su.get('is_admin') else None
    all_plans = remedy_store.list_plans(visible_uuids=visible)
    method_map = {m['key']: m for m in remedy_store.list_methods()}
    plans_in_range = []
    for p in all_plans:
        sd = p.get('scheduled_date') or ''
        if start_s <= sd <= end_s or sd >= start_s:
            m = method_map.get(p['method_key'], {})
            plans_in_range.append({
                'device': name_map.get(p['device_uuid'], {}).get('name') or p['device_uuid'],
                'method': m.get('name', p['method_key']),
                'scheduled_date': sd,
                'reduction_pct': m.get('reduction_pct'),
            })

    # 장비 상태
    battery_vals = [(d.get('device') or {}).get('battery') or 0 for d in devices]
    avg_battery = round(sum(battery_vals) / len(battery_vals)) if battery_vals else 0
    now_utc = datetime.now(timezone.utc)
    offline_count = 0; low_batt_count = 0
    for d in devices:
        dv = d.get('device') or {}
        if (dv.get('battery') or 100) < 15:
            low_batt_count += 1
        ud = dv.get('updated_date') or ''
        try:
            udt = datetime.fromisoformat(ud.replace('Z', '+00:00'))
            if (now_utc - udt).total_seconds() / 60 > 1440:
                offline_count += 1
        except Exception:
            offline_count += 1

    # GPT 프롬프트
    period_label = {'daily': '일간', 'weekly': '주간', 'monthly': '월간'}.get(period, '일간')
    top_devs_text = '\n'.join(
        f"  - {name_map.get(u, {}).get('name')} ({name_map.get(u, {}).get('addr') or '주소미상'}): 기간 합계 {v}마리"
        for u, v in dev_totals
    ) or '  - 데이터 없음'
    anomaly_text = '\n'.join(
        f"  - {a['date']} {a['name']}({a['addr'] or '주소미상'}) — {a['count']}마리 / 기준 {a['bad_min']}"
        for a in anomalies
    ) or '  - 기준 초과 이상 감지 없음'
    plans_text = '\n'.join(
        f"  - {p['device']} / {p['method']} / 예정 {p['scheduled_date']} / 감소율 {p['reduction_pct']}%"
        for p in plans_in_range[:10]
    ) or '  - 해당 기간 방역 계획 없음'

    # 종합 현황 KPI (최신일 기준) — 보고서에 AI 요약 근거로 포함
    try:
        ov = _build_overview_data(su)
        k = ov.get('kpi') or {}
        overview_block = (
            "\n■ 종합 현황 KPI (보고일 기준)\n"
            f"  - 오늘 포집 합계: {k.get('today_total', 0)}마리 (전일 대비 {k.get('change_pct', 0):+d}%)\n"
            f"  - 최다 포집 장비: {((k.get('top_dev') or {}).get('name') or '-')} · {(k.get('top_dev') or {}).get('count', 0)}마리\n"
            f"  - 경고 이상 장비: {k.get('warn_count', 0)}개\n"
            f"  - 오늘 기준 초과 감지: {k.get('anomaly_today', 0)}건\n"
            f"  - 민원 가능 '높음': {k.get('complaint_high', 0)}개\n"
            f"  - 장비 점검 필요: {k.get('equip_bad', 0)}대 (오프라인 {k.get('offline_count', 0)}/점검 {k.get('check_count', 0)})\n"
            f"  - 평균 데이터 신뢰도: {k.get('avg_trust', 0)}%\n"
        )
    except Exception as _e:
        overview_block = ''
        k = {}

    payload_summary = f"""[{period_label} 보고 기준 요약 · {start_s} ~ {end_s}]
{overview_block}
■ 기간 전체 수치
  - 전체 장비 수: {len(devices)}대
  - 기간 합계 포집량: {total_in_period}마리 (일평균 {avg_per_day}마리)
  - 측정 일수: {n_days}일
  - 오프라인 장비: {offline_count}대
  - 배터리 15% 미만 장비: {low_batt_count}대
  - 평균 배터리: {avg_battery}%

■ 기간 상위 포집 장비 (Top 5)
{top_devs_text}

■ 이상 감지 (장비 고유 기준 초과)
{anomaly_text}

■ 해당 기간 방역 계획
{plans_text}
"""

    api_key = getattr(dj_settings, 'OPENAI_API_KEY', '') or ''
    if not api_key:
        report_text = '※ OpenAI API 키가 서버에 설정되지 않아 AI 분석이 불가합니다.\n\n' + payload_summary
        source = 'fallback'
    else:
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            period_instruction = {
                'daily':   '오늘 하루를 기준으로 요약하십시오.',
                'weekly':  '최근 7일간의 추이를 중심으로 요약하십시오.',
                'monthly': '최근 30일간의 장기 추세와 계절적 특성을 반영하여 요약하십시오.',
            }.get(period, '요약하십시오.')
            resp = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {'role': 'system', 'content': (
                        f'당신은 지자체 보건소 감염병관리팀의 {period_label} 모기 발생 보고서 작성을 지원하는 AI입니다. '
                        f'{period_instruction} '
                        '주어진 데이터만으로 결재용 공문 형식의 보고서를 한국어로 작성하십시오. '
                        '다음 5개 섹션을 반드시 포함하십시오: '
                        '1) 핵심 수치 요약 '
                        '2) 이상 발생 및 주요 관측 사항 '
                        '3) 방역 실시 현황 '
                        '4) 향후 대응 권고 '
                        '5) 참고 · 특이사항. '
                        '각 섹션은 "■" 기호로 시작, 불릿은 "- "로 시작합니다. '
                        '공공기관 행정 어조(…함, …필요함, …권고함)를 사용하십시오. '
                        '결재란·서명란·날짜 줄은 포함하지 마세요 (화면에서 별도 렌더링됩니다).'
                    )},
                    {'role': 'user', 'content': payload_summary},
                ],
                temperature=0.4,
                max_tokens=900,
            )
            report_text = resp.choices[0].message.content.strip()
            source = 'openai:gpt-4o-mini'
        except Exception as e:
            logger.exception('OpenAI call failed in report')
            report_text = f'※ AI 분석 중 오류: {e}\n\n' + payload_summary
            source = 'error'

    # 섹션 2: 관측소별 현황 (ov['devices']에 이미 계산되어 있음)
    stations_section = []
    if ov:
        for d in ov.get('devices', []):
            stations_section.append({
                'name': d['name'], 'addr': d.get('addr', ''),
                'risk_level': d['risk_level'], 'risk_score': d['risk_score'],
                'today': d['today'], 'yday': d.get('yday', 0), 'week_avg': d.get('week_avg', 0),
                'complaint_level': d['complaint_level'],
                'status': d['status'], 'trust_score': d['trust_score'],
                'trend': d.get('trend', '·'),
            })

    # 섹션 3: 일간이면 시간별 히트맵 (48h raw로 허용 장비의 시간×장비)
    heatmap_section = None
    if period == 'daily':
        try:
            now_for_hm = datetime.now(timezone.utc)
            hm_start = (now_for_hm - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            hm_end = now_for_hm.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            hm_raw = moscom_client.get_statistics_by_date(
                start_dt=hm_start, end_dt=hm_end, aggregation='raw', device_uuid='0'
            )
            hm_raw = [r for r in (hm_raw or []) if r.get('device_uuid') in allowed_set]
            per_dev_hour = defaultdict(lambda: [None] * 24)
            for r in hm_raw:
                u = r.get('device_uuid')
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
            rows = []
            for u in allowed_uuids:
                hr = per_dev_hour.get(u, [None]*24)
                deltas = [0]*24; prev = 0
                for h in range(24):
                    v = hr[h]
                    if v is None: continue
                    d_ = v - prev; deltas[h] = d_ if d_ > 0 else 0; prev = v
                total = sum(deltas)
                rows.append({
                    'name': name_map.get(u, {}).get('name') or u,
                    'hours': deltas, 'total': total,
                })
            rows.sort(key=lambda x: x['total'], reverse=True)
            heatmap_section = rows[:30]  # 상위 30대
        except Exception:
            heatmap_section = None

    # 섹션 4: 이상 감지 상세 (anomalies는 이미 있음)
    anomaly_section = [
        {
            'name': a['name'], 'addr': a['addr'], 'date': a['date'],
            'count': a['count'], 'bad_min': a['bad_min'],
            'pct_over': round((a['count'] - a['bad_min']) / a['bad_min'] * 100) if a['bad_min'] else 0,
        }
        for a in anomalies
    ]

    # 섹션 5: AI 예측 — 기간에 따라 다르게 호출
    predict_section = None
    try:
        p_days = 3 if period == 'daily' else 7 if period == 'weekly' else 14
        p_inputs = []
        for u, m in name_map.items():
            hist = []
            for dt in sorted_dates[-10:] if False else sorted({dd for dd in daily[u]}):
                hist.append({'date': dt, 'count': daily[u].get(dt, 0)})
            hist.sort(key=lambda h: h['date'])
            p_inputs.append({
                'uuid': u, 'name': m['name'], 'region': m.get('addr') or '',
                'history': hist,
            })
        raw_preds = predictor.predict_for_devices(p_inputs, days_ahead=p_days)
        # 방역 효과 적용
        def _grade(n):
            if n <= 10: return '안전'
            if n <= 50: return '관심'
            if n <= 100: return '주의'
            if n <= 200: return '경고'
            return '위험'
        for p in raw_preds:
            new_preds = []
            for pp in p['predictions']:
                factor, _ = remedy_store.adjustment_factor(p['uuid'], pp.get('date'))
                orig = pp.get('predicted') or 0
                new_preds.append({
                    'date': pp['date'],
                    'predicted': int(round(orig * factor)),
                    'predicted_raw': orig,
                    'remedy_factor': round(factor, 3),
                })
            p['predictions'] = new_preds
            ps = [x['predicted'] for x in new_preds]
            p['max_predicted'] = max(ps) if ps else 0
            p['grade'] = _grade(p['max_predicted'])
        raw_preds.sort(key=lambda x: x.get('max_predicted', 0), reverse=True)
        # 위험 점수 상위 10대 + 날짜별 합계
        predict_section = {
            'devices': [
                {
                    'name': p['name'], 'grade': p['grade'],
                    'max_predicted': p['max_predicted'],
                    'predictions': p['predictions'],
                }
                for p in raw_preds[:10]
            ],
            'day_totals': [],
        }
        if raw_preds:
            dates0 = [pp['date'] for pp in raw_preds[0]['predictions']]
            for i, dt in enumerate(dates0):
                total = sum(p['predictions'][i]['predicted'] for p in raw_preds)
                predict_section['day_totals'].append({'date': dt, 'total': total})
    except Exception as e:
        logger.exception('predict section failed')
        predict_section = None

    summary = {
        'total_devices': len(devices),
        'period': period, 'period_label': period_label,
        'start_date': start_s, 'end_date': end_s,
        'total_in_period': total_in_period,
        'avg_per_day': avg_per_day,
        'n_days': n_days,
        'anomaly_count': len(anomalies),
        'offline_count': offline_count,
        'low_batt_count': low_batt_count,
        'plan_count': len(plans_in_range),
        'avg_battery': avg_battery,
        'overview_kpi': {
            'today_total': k.get('today_total', 0) if k else 0,
            'change_pct': k.get('change_pct', 0) if k else 0,
            'warn_count': k.get('warn_count', 0) if k else 0,
            'anomaly_today': k.get('anomaly_today', 0) if k else 0,
            'complaint_high': k.get('complaint_high', 0) if k else 0,
            'equip_bad': k.get('equip_bad', 0) if k else 0,
            'offline_count': k.get('offline_count', 0) if k else 0,
            'check_count': k.get('check_count', 0) if k else 0,
            'avg_trust': k.get('avg_trust', 0) if k else 0,
            'top_dev': k.get('top_dev') if k else None,
        } if k else None,
        # 풀 섹션
        'sections': {
            'stations': stations_section,
            'heatmap': heatmap_section,
            'anomaly': anomaly_section,
            'predict': predict_section,
            'plans': plans_in_range,
        },
    }
    return report_text, summary, allowed_uuids, source, payload_summary


def moscom_report_api(request):
    """보고서 생성(POST) + 자기 기록 목록(GET)"""
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    su = _current_session_user(request)
    if request.method == 'GET':
        # admin은 전체, 일반 사용자는 본인 기록만
        if su.get('is_admin'):
            reports = report_store.list_reports()
        else:
            reports = report_store.list_reports(author_login_id=su.get('login_id'))
        return JsonResponse({'reports': reports})
    try:
        body = _json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except _json.JSONDecodeError:
        body = {}
    if request.method == 'POST':
        period = body.get('period') or 'daily'
        if period not in ('daily', 'weekly', 'monthly'):
            return JsonResponse({'error': 'period는 daily/weekly/monthly 중 선택'}, status=400)
        base_date = body.get('base_date') or ''
        try:
            report_text, summary, scoped, source, payload = _build_report_body(period, base_date, su, request)
        except Exception as e:
            logger.exception('report body build failed')
            return JsonResponse({'error': f'보고서 데이터 수집 실패: {e}'}, status=500)

        record = {
            'author_login_id': su.get('login_id'),
            'period': period,
            'base_date': summary['end_date'],
            'org': (body.get('org') or '').strip()[:100],
            'department': (body.get('department') or '').strip()[:100],
            'writer_name': (body.get('writer_name') or '').strip()[:50],
            'writer_title': (body.get('writer_title') or '').strip()[:50],
            'reviewer_name': (body.get('reviewer_name') or '').strip()[:50],
            'reviewer_title': (body.get('reviewer_title') or '').strip()[:50],
            'approver_name': (body.get('approver_name') or '').strip()[:50],
            'approver_title': (body.get('approver_title') or '').strip()[:50],
            'summary': summary,
            'report_text': report_text,
            'source': source,
            'scoped_device_uuids': scoped,
        }
        saved = report_store.create_report(record)
        return JsonResponse({'ok': True, 'id': saved['id'], 'report': saved})
    return JsonResponse({'error': 'method not allowed'}, status=405)


def moscom_report_detail_api(request, report_id):
    """단일 보고서 조회 + 삭제(admin 전용)"""
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    su = _current_session_user(request)
    rec = report_store.get_report(report_id)
    if not rec:
        return JsonResponse({'error': '존재하지 않는 보고서'}, status=404)
    # 접근 권한: admin 또는 본인이 작성한 것만
    if not su.get('is_admin') and rec.get('author_login_id') != su.get('login_id'):
        return JsonResponse({'error': '권한 없음'}, status=403)
    if request.method == 'GET':
        return JsonResponse({'report': rec})
    if request.method == 'DELETE':
        if not su.get('is_admin'):
            return JsonResponse({'error': 'admin 전용'}, status=403)
        try:
            report_store.delete_report(report_id)
            return JsonResponse({'ok': True})
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'method not allowed'}, status=405)


def mosquito_report_view(request, report_id):
    """보고서 HTML 페이지 (브라우저에서 열고 인쇄/PDF 저장 가능)"""
    if not request.session.get('mosquito_auth'):
        from django.shortcuts import redirect
        return redirect('/mosquito-test/')
    su = _current_session_user(request)
    rec = report_store.get_report(report_id)
    if not rec:
        return HttpResponse('보고서를 찾을 수 없습니다', status=404)
    if not su.get('is_admin') and rec.get('author_login_id') != su.get('login_id'):
        return HttpResponse('접근 권한이 없습니다', status=403)
    # 히트맵 섹션 → JSON 문자열로 템플릿에 주입
    hm = ((rec.get('summary') or {}).get('sections') or {}).get('heatmap') or []
    return render(request, 'core/mosquito_report.html', {
        'report': rec,
        'heatmap_json': _json.dumps(hm, ensure_ascii=False),
    })


@require_GET
def moscom_admin_judgment(request):
    """AI 행정 판단 리포트 생성 (GPT 연동).
    모든 탭 데이터를 수집해서 요약 → OpenAI에 공문 형식 리포트 요청.
    캐싱 5분.
    """
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    from datetime import datetime, timedelta, timezone
    from django.core.cache import cache
    from django.conf import settings as dj_settings

    su = _current_session_user(request)
    # 사용자별 캐시 키
    cache_key = 'moscom:admin_judgment:' + (su.get('login_id') or 'anon')
    force = request.GET.get('refresh') == '1'
    if not force:
        cached = cache.get(cache_key)
        if cached is not None:
            return JsonResponse(cached)

    try:
        devices = moscom_client.list_devices()
        devices = user_store.filter_devices(su, devices)
        allowed_uuids = {d.get('device_uuid') for d in devices}

        # 7일 통계
        stats = moscom_client.get_statistics(device_uuid='', period_type='2', offset=0)
        stats = [r for r in (stats or []) if r.get('device_uuid') in allowed_uuids]

        # 일별 집계 (장비당)
        from collections import defaultdict
        daily = defaultdict(lambda: defaultdict(int))
        dates = set()
        for r in stats:
            u = r.get('device_uuid')
            date = (r.get('created_date') or '')[:10]
            if u and date:
                daily[u][date] += (r.get('mosquito_count') or 0)
                dates.add(date)
        sorted_dates = sorted(dates)
        today = sorted_dates[-1] if sorted_dates else ''
        yday = sorted_dates[-2] if len(sorted_dates) >= 2 else ''

        # 오늘 합계 + 어제 대비
        today_total = sum(daily[u].get(today, 0) for u in daily) if today else 0
        yday_total = sum(daily[u].get(yday, 0) for u in daily) if yday else 0
        pct = round((today_total - yday_total) / yday_total * 100) if yday_total else 0

        # 오늘 장비 탑 5
        today_devs = sorted(
            [(u, daily[u].get(today, 0)) for u in daily.keys()],
            key=lambda x: x[1], reverse=True
        )[:5]

        # 장비 이름 매핑
        name_map = {}
        for d in devices:
            dv = d.get('device') or {}
            nm = (dv.get('device_name') or '').strip() or d.get('device_uuid')
            addr = ' '.join(p for p in [dv.get('address_gungu'), dv.get('address_dong')] if p and len(p) < 40) or ''
            name_map[d.get('device_uuid')] = {'name': nm, 'addr': addr, 'bad_min': ((dv.get('deviceSetting') or {}).get('bad_min')) or 100}

        # 이상 감지 요약 (bad_min 초과)
        anomalies = []
        for u, v in today_devs:
            meta = name_map.get(u, {})
            if v >= meta.get('bad_min', 100) and meta.get('bad_min', 0) > 0:
                anomalies.append(f"{meta.get('name')}({meta.get('addr') or '주소미상'}) — 오늘 {v}마리 / 기준 {meta.get('bad_min')} 초과")

        # 방역 계획 현황
        from core import remedy_store
        visible = allowed_uuids if not su.get('is_admin') else None
        plans = remedy_store.list_plans(visible_uuids=visible)
        method_map = {m['key']: m for m in remedy_store.list_methods()}
        active_plans = []
        for p in plans[:20]:
            m = method_map.get(p['method_key'], {})
            active_plans.append({
                'device': name_map.get(p['device_uuid'], {}).get('name') or p['device_uuid'],
                'method': m.get('name', p['method_key']),
                'scheduled_date': p['scheduled_date'],
                'reduction_pct': m.get('reduction_pct'),
            })

        # 장비 상태 대략 (배터리 평균, 오프라인 수)
        battery_vals = [(d.get('device') or {}).get('battery') or 0 for d in devices]
        avg_battery = round(sum(battery_vals) / len(battery_vals)) if battery_vals else 0
        # 수신 지연으로 오프라인 판별
        now_utc = datetime.now(timezone.utc)
        offline_count = 0
        low_batt_count = 0
        for d in devices:
            dv = d.get('device') or {}
            if (dv.get('battery') or 100) < 15:
                low_batt_count += 1
            ud = dv.get('updated_date') or ''
            try:
                udt = datetime.fromisoformat(ud.replace('Z', '+00:00'))
                if (now_utc - udt).total_seconds() / 60 > 1440:
                    offline_count += 1
            except Exception:
                offline_count += 1

        # ── GPT 프롬프트 구성 ────────────────────────
        top_devs_text = '\n'.join(
            f"  - {name_map.get(u, {}).get('name')} ({name_map.get(u, {}).get('addr') or '주소미상'}): {v}마리"
            for u, v in today_devs
        ) or '  - 데이터 없음'
        anomaly_text = '\n'.join(f"  - {a}" for a in anomalies) or '  - 기준 초과 장비 없음'
        plans_text = '\n'.join(
            f"  - {p['device']} / {p['method']} / 예정 {p['scheduled_date']} / 감소율 {p['reduction_pct']}%"
            for p in active_plans
        ) or '  - 등록된 방역 계획 없음'

        date_label = today or datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
        payload_summary = f"""[모기 발생 감시 현황 · {date_label}]

■ 전체 수치
  - 전체 장비 수: {len(devices)}대
  - 오늘 포집 합계: {today_total}마리 (전일 {yday_total}마리, 변화 {pct:+d}%)
  - 오프라인 장비: {offline_count}대
  - 배터리 15% 미만 장비: {low_batt_count}대
  - 평균 배터리: {avg_battery}%

■ 오늘 상위 포집 장비 (Top 5)
{top_devs_text}

■ 이상 감지 (장비 고유 기준 초과)
{anomaly_text}

■ 진행/예정 방역 계획
{plans_text}
"""

        # OpenAI 호출
        api_key = getattr(dj_settings, 'OPENAI_API_KEY', '') or ''
        if not api_key:
            report_text = '※ OpenAI API 키가 서버에 설정되지 않아 AI 분석이 불가합니다.\n\n' + payload_summary
            source = 'fallback'
        else:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model='gpt-4o-mini',
                    messages=[
                        {'role': 'system', 'content': (
                            '당신은 지자체 보건소 감염병관리팀의 행정 보고서 작성을 지원하는 AI입니다. '
                            '주어진 데이터를 바탕으로 결재용 공문 형식의 "행정 판단 보고"를 한국어로 작성하십시오. '
                            '과장 없이 데이터 근거로 기술하고, 다음 5개 섹션을 반드시 포함하십시오: '
                            '1) 오늘 핵심 수치 요약 '
                            '2) 즉시 조치 필요 사항 (없으면 "해당 없음") '
                            '3) AI 예측 요약 '
                            '4) 진행 중인 방역 현황 '
                            '5) AI 행정 권고 (우선순위별 불릿). '
                            '각 섹션은 "■" 기호로 시작하고, 불릿은 "- "로 시작합니다. '
                            '문장은 공공기관 행정 어조(…함, …필요함, …권고함)로 작성하세요. '
                            '결재란·서명란·날짜 줄은 포함하지 마세요 (화면에서 별도 렌더링됩니다).'
                        )},
                        {'role': 'user', 'content': payload_summary},
                    ],
                    temperature=0.5,
                    max_tokens=800,
                )
                report_text = resp.choices[0].message.content.strip()
                source = 'openai:gpt-4o-mini'
            except Exception as e:
                logger.exception('OpenAI call failed')
                report_text = f'※ AI 분석 중 오류가 발생했습니다: {e}\n\n' + payload_summary
                source = 'error'

        result = {
            'report_text': report_text,
            'source': source,
            'generated_at': datetime.now(timezone(timedelta(hours=9))).isoformat(),
            'author': {'login_id': su.get('login_id'), 'is_admin': su.get('is_admin')},
            'summary': {
                'total_devices': len(devices),
                'today_total': today_total,
                'yday_total': yday_total,
                'change_pct': pct,
                'anomaly_count': len(anomalies),
                'offline_count': offline_count,
                'low_batt_count': low_batt_count,
                'plan_count': len(active_plans),
            },
        }
        cache.set(cache_key, result, 300)
        return JsonResponse(result)
    except Exception as e:
        logger.exception('admin_judgment failed')
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def moscom_equipment_health(request):
    """장비 신뢰도 점수화 (4축)
    - 배터리: 현재 battery%
    - 팬 작동: fan (1=정상, 0=정지)
    - 수신 지연: 현재 시각 - updated_date (분)
    - 포집 0 지속: 최근 3일간 mosquito_count 모두 0
    """
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    from datetime import datetime, timedelta, timezone
    from collections import defaultdict
    try:
        now = datetime.now(timezone.utc)
        devices = moscom_client.list_devices()
        devices = user_store.filter_devices(_current_session_user(request), devices)

        # 최근 3일 일별 통계
        stats = moscom_client.get_statistics(device_uuid='', period_type='2', offset=0)
        daily = defaultdict(lambda: defaultdict(int))
        for r in (stats or []):
            u = r.get('device_uuid')
            date = (r.get('created_date') or '')[:10]
            if u and date:
                daily[u][date] += (r.get('mosquito_count') or 0)

        def parse_iso(s):
            if not s:
                return None
            try:
                s2 = s.replace('Z', '+00:00')
                return datetime.fromisoformat(s2)
            except Exception:
                return None

        results = []
        for d in devices:
            u = d.get('device_uuid')
            dv = d.get('device') or {}
            name = (dv.get('device_name') or '').strip() or u
            battery = dv.get('battery') or 0
            fan = dv.get('fan') or 0
            charge = dv.get('charge') or 0
            updated = parse_iso(dv.get('updated_date'))

            # 축 1: 배터리 (0~100점)
            if battery >= 50: axis_battery = 100
            elif battery >= 30: axis_battery = 80
            elif battery >= 20: axis_battery = 60
            elif battery >= 10: axis_battery = 35
            else: axis_battery = 10
            # 축 2: 팬
            axis_fan = 100 if fan == 1 else 30

            # 축 3: 수신 지연
            if updated:
                delay_min = (now - updated).total_seconds() / 60
            else:
                delay_min = 99999
            if delay_min <= 120: axis_signal = 100     # 2h 이내
            elif delay_min <= 360: axis_signal = 80    # 6h
            elif delay_min <= 720: axis_signal = 55    # 12h
            elif delay_min <= 1440: axis_signal = 30   # 24h
            else: axis_signal = 5                      # 24h 초과

            # 축 4: 포집 0 지속 — 최근 3일치 합
            dev_daily = daily.get(u, {})
            recent_vals = list(dev_daily.values())
            total3 = sum(recent_vals[-3:]) if recent_vals else 0
            if len(recent_vals) >= 3 and total3 == 0:
                axis_zero = 40  # 3일 내내 0 → 센서 의심
            elif total3 == 0:
                axis_zero = 65  # 데이터 부족
            else:
                axis_zero = 100

            # 가중치: 배터리 25 / 팬 20 / 수신 35 / 포집0 20
            trust_score = round(
                axis_battery * 0.25 + axis_fan * 0.20 + axis_signal * 0.35 + axis_zero * 0.20, 1
            )

            # 등급
            if trust_score >= 85: trust = 'HIGH'
            elif trust_score >= 60: trust = 'MEDIUM'
            else: trust = 'LOW'

            # 장비 상태 판정
            if axis_signal <= 30:
                status = '오프라인'
            elif trust_score < 60 or battery < 15 or (fan == 0 and axis_signal >= 55):
                status = '점검필요'
            else:
                status = '정상'

            # 이상 원인 수집
            issues = []
            if battery < 20: issues.append(f'배터리 부족 ({battery}%)')
            if fan == 0: issues.append('팬 정지')
            if delay_min > 720: issues.append(f'수신 지연 {int(delay_min/60)}시간')
            elif delay_min > 360: issues.append(f'수신 지연 {int(delay_min/60)}시간')
            if axis_zero == 40: issues.append('3일 연속 포집 0 (센서 의심)')

            # 조치 안내
            if status == '오프라인':
                action = '현장 방문 · 전원·통신 점검'
            elif battery < 15:
                action = '배터리 교체 필요'
            elif fan == 0:
                action = '팬 점검 · 재기동'
            elif axis_zero == 40:
                action = '센서부 청소 점검'
            elif trust == 'HIGH':
                action = '정상 운영 중'
            else:
                action = '원격 상태 모니터링'

            parts = [dv.get('address_gungu'), dv.get('address_dong')]
            addr = ' '.join(p for p in parts if p and len(p) < 40 and any('\uac00' <= c <= '\ud7a3' or c.isalnum() or c == ' ' for c in p)).strip()

            results.append({
                'uuid': u,
                'name': name,
                'address': addr,
                'battery': battery,
                'fan': fan,
                'charge': charge,
                'updated_date': dv.get('updated_date'),
                'delay_minutes': round(delay_min, 1) if delay_min < 99999 else None,
                'status': status,
                'trust': trust,
                'trust_score': trust_score,
                'axes': {
                    '배터리': axis_battery,
                    '팬': axis_fan,
                    '수신': axis_signal,
                    '포집': axis_zero,
                },
                'issues': issues,
                'action': action,
            })

        results.sort(key=lambda r: (r['trust_score'], r['delay_minutes'] or 0))

        # 집계
        summary = {
            'total': len(results),
            'normal': sum(1 for r in results if r['status'] == '정상'),
            'check': sum(1 for r in results if r['status'] == '점검필요'),
            'offline': sum(1 for r in results if r['status'] == '오프라인'),
            'avg_trust': round(sum(r['trust_score'] for r in results) / len(results), 1) if results else 0,
        }

        return JsonResponse({
            'count': len(results),
            'summary': summary,
            'criteria': {
                'weights': {'배터리': 25, '팬': 20, '수신': 35, '포집': 20},
                'trust': {'HIGH': '≥ 85', 'MEDIUM': '60~84', 'LOW': '< 60'},
            },
            'items': results,
        })
    except Exception as e:
        logger.exception('equipment_health failed')
        return JsonResponse({'error': str(e)}, status=500)


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
        body = _json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
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
        body = _json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
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


@require_GET
def kakao_status(request):
    """현재 로그인 사용자의 카카오 연동 상태"""
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    su = _current_session_user(request)
    entry = kakao_client.get_token(su.get('login_id'))
    if not entry:
        return JsonResponse({'connected': False})
    return JsonResponse({
        'connected': True,
        'connected_at': entry.get('connected_at'),
        'access_expires_at': entry.get('access_expires_at'),
        'scopes': entry.get('scopes') or [],
    })


def kakao_oauth_start(request):
    """카카오 OAuth 시작 — 로그인 페이지로 리다이렉트"""
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    from django.shortcuts import redirect
    url = kakao_client.authorize_url()
    return redirect(url)


def kakao_oauth_callback(request):
    """카카오가 code와 함께 돌아오는 지점"""
    if not request.session.get('mosquito_auth'):
        from django.shortcuts import redirect
        return redirect('/mosquito-test/')
    su = _current_session_user(request)
    code = request.GET.get('code')
    err = request.GET.get('error')
    if err:
        return HttpResponse(f'<h3>카카오 인증 실패</h3><p>{err}: {request.GET.get("error_description","")}</p><p><a href="/mosquito-test/">돌아가기</a></p>', status=400)
    if not code:
        return HttpResponse('code 없음', status=400)
    try:
        payload = kakao_client.exchange_code(code)
        kakao_client.save_tokens_for(su.get('login_id'), payload)
    except Exception as e:
        logger.exception('kakao exchange failed')
        return HttpResponse(f'토큰 교환 실패: {e}', status=500)
    # 완료 후 관리자 탭으로 돌려보냄
    return HttpResponse(
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>연동 완료</title></head>'
        '<body style="font-family:sans-serif;text-align:center;padding:50px">'
        '<h2 style="color:#1B3A6B">카카오톡 연동 완료</h2>'
        '<p>이제 대시보드에서 "나에게 알림 보내기"를 사용할 수 있습니다.</p>'
        '<p><a href="/mosquito-test/" style="color:#2980b9">대시보드로 돌아가기</a></p>'
        '<script>if(window.opener){window.opener.postMessage({type:"kakao-connected"},"*");setTimeout(()=>window.close(),1500)}</script>'
        '</body></html>'
    )


def kakao_disconnect(request):
    """연동 해제 (토큰 삭제)"""
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    su = _current_session_user(request)
    kakao_client.delete_token(su.get('login_id'))
    return JsonResponse({'ok': True})


def kakao_send_api(request):
    """나에게 보내기"""
    auth_err = _require_mosquito_auth(request)
    if auth_err:
        return auth_err
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try:
        body = _json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except _json.JSONDecodeError:
        body = {}
    text = (body.get('text') or '').strip()
    link = body.get('link') or 'https://saerong.com/mosquito-test/'
    if not text:
        return JsonResponse({'error': '메시지 내용이 비어있습니다'}, status=400)
    su = _current_session_user(request)
    ok, detail = kakao_client.send_to_me(su.get('login_id'), text, link_url=link)
    if not ok:
        return JsonResponse({'error': str(detail)}, status=400)
    return JsonResponse({'ok': True, 'result': detail})


def moscom_user_detail_api(request, login_id):
    admin_err = _require_admin(request)
    if admin_err:
        return admin_err
    try:
        body = _json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
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

        # MOSCOM의 "업무일"은 KST 10:00 ~ 다음날 09:59 수집.
        # 선택한 날짜 D는 "D일 10:00 KST ~ (D+1)일 10:00 KST" 로 해석.
        # start_utc = start_d 10:00 KST (-> UTC 01:00)
        # end_utc   = (end_d + 1) 10:00 KST (-> 다음날 UTC 01:00) exclusive
        start_utc = datetime(start_d.year, start_d.month, start_d.day, 10, 0, 0, tzinfo=timezone.utc) - timedelta(hours=9)
        end_utc = datetime(end_d.year, end_d.month, end_d.day, 10, 0, 0, tzinfo=timezone.utc) + timedelta(days=1) - timedelta(hours=9)
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

        # 히스토리는 오름차순(과거 → 최신)으로 정렬: 차트와 lag 계산에 필요
        for u in hist_by_uuid:
            hist_by_uuid[u].sort(key=lambda h: h['date'])

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
                'trained_on': '3개 관측소 · 2025년 7~8월 · 187건',
                'features': 34,
            },
            'disclaimer': '학습 데이터: 3개 관측소 · 2025년 7~8월. 다른 지역/계절은 참고값.',
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
