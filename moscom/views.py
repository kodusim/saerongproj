"""moscom DB 기반 조회 + 수정 API.

조회: 누구나 (기존 mosquito-test 처럼)
수정: 관리자만 (request.session 의 'mosquito_admin' 또는 staff)
"""
import json
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Count, Q

from .models import Device, Collection, SyncState, EditLog, Region
from .edit_helpers import log_change


def _is_admin(request):
    # 기존 mosquito-test 가 쓰던 세션 키 그대로
    if request.session.get('mosquito_admin'):
        return True
    if getattr(request.user, 'is_staff', False):
        return True
    return False


def _allowed_uuids(request):
    """로그인 사용자의 허용 장비 UUID 집합. admin/미인증세션은 None(=전체).
    /db/ 엔드포인트도 mosquito-test 세션 권한(allowed_devices)을 따르도록.
    """
    try:
        from core import views as core_views, user_store
        su = core_views._current_session_user(request)
        return user_store.allowed_uuid_set(su)  # admin → None
    except Exception:
        return None


def _admin_name(request):
    if request.session.get('mosquito_admin'):
        return 'mosquito_admin'
    if getattr(request.user, 'is_authenticated', False):
        return request.user.username
    return ''


# ─ 수동 동기화 ─────────────────────────────────

@csrf_exempt
@require_POST
def manual_resync(request):
    """관리자: MOSCOM API에서 데이터 다시 가져오기 (수동 갱신).
    body: {days?: int=7, overwrite_edited?: bool=False}
    overwrite_edited=False: 이미 저장된 행은 건드리지 않음 (수정값 보존)
    overwrite_edited=True : 모든 행을 원본으로 덮어씀 (수정 이력은 EditLog 에 남음)
    """
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        body = {}
    try:
        days = max(1, min(int(body.get('days') or 7), 90))
    except (TypeError, ValueError):
        days = 7
    overwrite = bool(body.get('overwrite_edited', False))

    try:
        from .sync import sync_devices, backfill_collections
        dev_r = sync_devices()
        col_r = backfill_collections(days=days, overwrite_edited=overwrite)
        return JsonResponse({
            'ok': True,
            'devices': dev_r,
            'collections': col_r,
            'overwrite_edited': overwrite,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ─ 기간별 집계 ────────────────────────────────

@require_GET
def period_aggregate(request):
    """기간별 집계 — 일/주/월/년 단위.
    데이터 소스: MOSCOM API 일별 집계(get_statistics_by_date aggregation='day').
    로컬 Collection 의 누적 카운터를 Sum 하면 폭증하므로, 종합현황·추세와 동일하게
    MOSCOM 의 일별 정확값을 받아 unit 단위로 버킷팅한다.
    params: start, end (YYYY-MM-DD), unit (day|week|month|year), device_uuid?, region_code?
    """
    from datetime import datetime as dt, timedelta, timezone as _tz
    from collections import defaultdict
    from core import moscom_client

    unit = (request.GET.get('unit') or 'day').strip().lower()
    if unit not in ('day', 'week', 'month', 'year'):
        return JsonResponse({'error': 'unit must be day|week|month|year'}, status=400)

    start_s = request.GET.get('start')
    end_s = request.GET.get('end')
    try:
        start_d = dt.fromisoformat(start_s).date() if start_s else None
        end_d = dt.fromisoformat(end_s).date() if end_s else None
    except ValueError:
        return JsonResponse({'error': 'date format YYYY-MM-DD'}, status=400)
    if not start_d or not end_d:
        return JsonResponse({'error': 'start, end 필요 (YYYY-MM-DD)'}, status=400)
    if end_d < start_d:
        start_d, end_d = end_d, start_d

    device_uuid = request.GET.get('device_uuid') or ''
    region_code = request.GET.get('region_code')

    # 사용자 권한 필터 (여수보건소=YS만 허용 시 다른 권역 차단). admin=None=전체
    allowed_uuids = _allowed_uuids(request)

    # 권역 필터 → 해당 권역 device_uuid 집합
    region_uuids = None
    if region_code:
        region_uuids = set(
            Device.objects.filter(region_code=region_code, is_active=True)
            .values_list('device_uuid', flat=True)
        )

    # MOSCOM 일별 집계 — 업무일 경계(KST 10:00) 적용해 start~end 커버
    start_utc = dt(start_d.year, start_d.month, start_d.day, 10, 0, 0, tzinfo=_tz.utc) - timedelta(hours=9)
    end_utc = dt(end_d.year, end_d.month, end_d.day, 10, 0, 0, tzinfo=_tz.utc) + timedelta(days=1) - timedelta(hours=9)
    start_iso = start_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    end_iso = end_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    try:
        raw = moscom_client.get_statistics_by_date(
            start_dt=start_iso, end_dt=end_iso, aggregation='day',
            device_uuid=device_uuid or '0',
        ) or []
    except Exception as e:
        return JsonResponse({'error': f'MOSCOM 조회 실패: {e}'}, status=502)

    devices = {d.device_uuid: d for d in Device.objects.all()}
    region_name_by_code = {r.code: r.name for r in Region.objects.all()}

    def bucket_key(date_str):
        # date_str: 'YYYY-MM-DD' → unit 버킷 키
        try:
            d = dt.strptime(date_str[:10], '%Y-%m-%d').date()
        except ValueError:
            return None
        if unit == 'day':
            return d.isoformat()
        if unit == 'week':
            monday = d - timedelta(days=d.weekday())
            return monday.isoformat()
        if unit == 'month':
            return f'{d.year}-{d.month:02d}-01'
        return f'{d.year}-01-01'  # year

    # (bucket, uuid) → {total, days, max}
    agg = defaultdict(lambda: {'total': 0, 'days': 0, 'max': 0})
    for r in raw:
        u = r.get('device_uuid')
        if not u:
            continue
        if allowed_uuids is not None and u not in allowed_uuids:
            continue  # 권한 없는 관측소 차단
        if device_uuid and u != device_uuid:
            continue
        if region_uuids is not None and u not in region_uuids:
            continue
        ds = (r.get('created_date') or '')[:10]
        # start~end 범위 밖(경계 보정으로 들어온 날짜) 제외
        if not ds or ds < start_d.isoformat() or ds > end_d.isoformat():
            continue
        bk = bucket_key(ds)
        if not bk:
            continue
        cnt = r.get('mosquito_count') or 0
        a = agg[(bk, u)]
        a['total'] += cnt      # 서로 다른 날의 일별값 합 (누적 아님 — 정상)
        a['days'] += 1
        if cnt > a['max']:
            a['max'] = cnt

    items = []
    for (bk, u), a in agg.items():
        d = devices.get(u)
        items.append({
            'bucket': bk,
            'device_uuid': u,
            'device_name': d.device_name if d else u,
            'region_code': (d.region_code if d else '') or '',
            'region_name': region_name_by_code.get((d.region_code if d else ''), '미지정') if d else '미지정',
            'total': a['total'],
            'events': a['days'],  # 버킷 내 데이터 보유 일수
            'avg': round(a['total'] / a['days'], 2) if a['days'] else 0,
            'max': a['max'],
        })
    items.sort(key=lambda x: (x['bucket'], x['device_uuid']))

    # bucket 단위 총합
    bucket_totals = {}
    for it in items:
        b = it['bucket']
        if b not in bucket_totals:
            bucket_totals[b] = {'bucket': b, 'total': 0, 'devices': 0}
        bucket_totals[b]['total'] += it['total']
        bucket_totals[b]['devices'] += 1
    bucket_summary = sorted(bucket_totals.values(), key=lambda x: x['bucket'])

    return JsonResponse({
        'unit': unit,
        'count': len(items),
        'items': items,
        'summary': bucket_summary,
    })


# ─ 장비 ────────────────────────────────────────

@require_GET
def device_list(request):
    qs = Device.objects.filter(is_active=True)
    # 사용자 권한 필터 (허용 장비 외 차단). admin=None=전체
    allowed_uuids = _allowed_uuids(request)
    if allowed_uuids is not None:
        qs = qs.filter(device_uuid__in=allowed_uuids)
    sido = request.GET.get('sido')
    region_code = request.GET.get('region_code')
    if sido:
        qs = qs.filter(address_sido=sido)
    if region_code is not None:
        qs = qs.filter(region_code=region_code)
    # 권역명 lookup
    region_map = {r.code: r.name for r in Region.objects.all()}
    return JsonResponse({
        'count': qs.count(),
        'items': [
            {
                'id': d.id,
                'device_uuid': d.device_uuid,
                'device_name': d.device_name,
                'address_sido': d.address_sido,
                'address_gungu': d.address_gungu,
                'address_dong': d.address_dong,
                'address_detail': d.address_detail,
                'latitude': d.latitude,
                'longitude': d.longitude,
                'current_mosquito_count': d.current_mosquito_count,
                'current_battery': d.current_battery,
                'current_charge': d.current_charge,
                'current_fan': d.current_fan,
                'updated_date': d.updated_date.isoformat() if d.updated_date else None,
                'thresholds': {
                    'normal_max': d.normal_max,
                    'warning_max': d.warning_max,
                    'bad_min': d.bad_min,
                },
                'temperature': d.temperature,
                'humidity': d.humidity,
                'precipitation': d.precipitation,
                'wind_speed': d.wind_speed,
                'weather_synced_at': d.weather_synced_at.isoformat() if d.weather_synced_at else None,
                'region_code': d.region_code,
                'region_name': region_map.get(d.region_code, d.region_code) or '기타',
                'region_type': d.region_type,
                'form_type': d.form_type,
            }
            for d in qs
        ],
    })


@require_GET
def region_list(request):
    """권역 목록. 각 권역별 장비 수 포함."""
    from collections import Counter
    dev_qs = Device.objects.filter(is_active=True)
    # 사용자 권한 필터 (허용 장비 권역만 노출). admin=None=전체
    allowed_uuids = _allowed_uuids(request)
    if allowed_uuids is not None:
        dev_qs = dev_qs.filter(device_uuid__in=allowed_uuids)
    counts = Counter(dev_qs.values_list('region_code', flat=True))
    regions = list(Region.objects.all())
    # 일반 사용자는 허용 장비가 있는 권역만 노출(권한 밖 권역 숨김). admin(allowed_uuids=None)은 전체.
    restrict = allowed_uuids is not None
    # DB 에 없지만 Device 에 prefix 있는 경우 — 빈 row 도 노출
    existing_codes = {r.code for r in regions}
    extra_codes = sorted(set(counts.keys()) - existing_codes - {''})
    etc_count = counts.get('', 0)
    items = [
        {
            'id': r.id, 'code': r.code, 'name': r.name,
            'overview_name': r.overview_name,
            'sort_order': r.sort_order, 'note': r.note,
            'device_count': counts.get(r.code, 0),
        }
        for r in regions
        if (not restrict) or counts.get(r.code, 0) > 0
    ] + [
        # Region 마스터에 없지만 Device 에는 prefix 있는 경우 (lazy)
        {'id': None, 'code': c, 'name': c, 'overview_name': '', 'sort_order': 100, 'note': '',
         'device_count': counts.get(c, 0)}
        for c in extra_codes
    ]
    # 앞 알파벳 2글자 없는 관측소 → '기타' 권역으로 묶어 노출
    if etc_count:
        items.append({'id': None, 'code': '', 'name': '기타', 'sort_order': 999,
                      'note': '권역 코드(앞 알파벳 2글자) 없음', 'device_count': etc_count})
    return JsonResponse({
        'items': items,
        'unassigned_device_count': etc_count,
    })


@csrf_exempt
@require_http_methods(['POST', 'PUT', 'PATCH'])
def region_upsert(request, code=None):
    """관리자만. POST /regions/  body:{code,name,sort_order,note}.
    PUT /regions/<code>/  표시명 등 수정."""
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON 파싱 실패'}, status=400)
    actor = _admin_name(request)
    if request.method == 'POST':
        code_in = (body.get('code') or '').strip()[:20]
        if not code_in:
            return JsonResponse({'error': 'code 필수'}, status=400)
        r, created = Region.objects.get_or_create(
            code=code_in,
            defaults={
                'name': (body.get('name') or code_in)[:80],
                'sort_order': int(body.get('sort_order') or 100),
                'note': (body.get('note') or '')[:200],
            },
        )
        if not created:
            return JsonResponse({'error': '이미 존재하는 코드'}, status=400)
        log_change('moscom.Region', r.id, '_created', '', f'{r.code}={r.name}', edited_by=actor)
        return JsonResponse({'ok': True, 'id': r.id})

    # PUT/PATCH — code (URL) 로 찾아서 수정
    if not code:
        return JsonResponse({'error': 'code 필요'}, status=400)
    r = Region.objects.filter(code=code).first()
    if not r:
        # 없으면 자동 생성 (lazy code 케이스)
        r = Region.objects.create(code=code, name=code, sort_order=100)
    for k in ['name', 'overview_name', 'sort_order', 'note']:
        if k in body:
            old = getattr(r, k)
            new = body[k]
            if k == 'sort_order':
                try: new = int(new)
                except (TypeError, ValueError): continue
            if k in ('name', 'note', 'overview_name'):
                new = (new or '')[:200 if k == 'note' else 80]
            if old != new:
                log_change('moscom.Region', r.id, k, old, new, edited_by=actor)
                setattr(r, k, new)
    r.save()
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(['DELETE'])
def region_delete(request, code):
    """관리자만. 권역 마스터 삭제 (Device.region_code 는 그대로 — code 만 사라짐)."""
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    r = Region.objects.filter(code=code).first()
    if not r:
        return JsonResponse({'error': '존재하지 않음'}, status=404)
    actor = _admin_name(request)
    log_change('moscom.Region', r.id, '_deleted', f'{r.code}={r.name}', '', edited_by=actor)
    r.delete()
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(['PUT', 'PATCH'])
def device_update(request, device_id):
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        d = Device.objects.get(id=device_id)
    except Device.DoesNotExist:
        return JsonResponse({'error': '장비 없음'}, status=404)
    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON 파싱 실패'}, status=400)
    EDITABLE = ['device_name', 'address_sido', 'address_gungu', 'address_dong',
                'address_detail', 'latitude', 'longitude', 'on_time', 'co2_on_time',
                'normal_max', 'warning_max', 'bad_min',
                'region_type', 'form_type']
    actor = _admin_name(request)
    for k in EDITABLE:
        if k in body:
            old = getattr(d, k)
            new = body[k]
            if old != new:
                log_change('moscom.Device', d.id, k, old, new, edited_by=actor)
                setattr(d, k, new)
    d.save()
    return JsonResponse({'ok': True})


# ─ 포집 데이터 ─────────────────────────────────

@require_GET
def collections(request):
    """포집 raw 조회.
    파라미터:
      start, end (ISO datetime, 옵셔널) — 둘 다 없으면 최근 24시간
      device_uuid (옵셔널)
      limit (기본 5000)
      agg = none|hourly|daily (옵셔널, 집계)
    """
    end_str = request.GET.get('end')
    start_str = request.GET.get('start')
    end = parse_datetime(end_str) if end_str else timezone.now()
    if start_str:
        start = parse_datetime(start_str)
    else:
        start = end - timedelta(hours=24)
    if not start or not end:
        return JsonResponse({'error': '날짜 파싱 실패'}, status=400)
    if timezone.is_naive(start):
        start = timezone.make_aware(start)
    if timezone.is_naive(end):
        end = timezone.make_aware(end)

    device_uuid = request.GET.get('device_uuid')
    agg = (request.GET.get('agg') or 'none').strip().lower()
    limit = min(int(request.GET.get('limit') or 5000), 20000)

    qs = Collection.objects.filter(created_date__gte=start, created_date__lte=end)
    if device_uuid:
        qs = qs.filter(device_uuid=device_uuid)

    if agg == 'none':
        rows = list(qs.order_by('-created_date')[:limit].values(
            'id', 'moscom_id', 'device_uuid', 'mosquito_count', 'battery',
            'charge', 'fan', 'reset', 'created_date', 'edited',
        ))
        for r in rows:
            r['created_date'] = r['created_date'].isoformat() if r['created_date'] else None
        return JsonResponse({'count': len(rows), 'items': rows})

    # 집계
    if agg == 'hourly':
        from django.db.models.functions import TruncHour
        qs = qs.annotate(bucket=TruncHour('created_date'))
    elif agg == 'daily':
        from django.db.models.functions import TruncDate
        qs = qs.annotate(bucket=TruncDate('created_date'))
    else:
        return JsonResponse({'error': 'agg 는 none|hourly|daily'}, status=400)

    rows = list(
        qs.values('bucket', 'device_uuid')
          .annotate(total=Sum('mosquito_count'), events=Count('id'))
          .order_by('bucket', 'device_uuid')
    )
    for r in rows:
        b = r['bucket']
        r['bucket'] = b.isoformat() if hasattr(b, 'isoformat') else str(b)
    return JsonResponse({'count': len(rows), 'items': rows, 'agg': agg})


@csrf_exempt
@require_http_methods(['PUT', 'PATCH', 'DELETE'])
def collection_detail(request, collection_id):
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    try:
        c = Collection.objects.get(id=collection_id)
    except Collection.DoesNotExist:
        return JsonResponse({'error': '없음'}, status=404)
    actor = _admin_name(request)

    if request.method == 'DELETE':
        log_change('moscom.Collection', c.id, '_deleted', f'mc={c.mosquito_count},ts={c.created_date}', '', edited_by=actor)
        c.delete()
        return JsonResponse({'ok': True})

    try:
        body = json.loads((request.body or b'').decode('utf-8', errors='replace') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON 파싱 실패'}, status=400)
    EDITABLE = ['mosquito_count', 'battery', 'charge', 'fan', 'reset', 'created_date']
    changed = False
    for k in EDITABLE:
        if k not in body:
            continue
        old = getattr(c, k)
        new = body[k]
        if k == 'created_date' and isinstance(new, str):
            parsed = parse_datetime(new)
            if parsed is None:
                return JsonResponse({'error': f'{k} 형식 오류'}, status=400)
            new = parsed
        if old != new:
            log_change('moscom.Collection', c.id, k, old, new, edited_by=actor)
            setattr(c, k, new)
            changed = True
    if changed:
        c.edited = True
        c.save()
    return JsonResponse({'ok': True})


# ─ 동기화 상태 ────────────────────────────────

@require_GET
def sync_status(request):
    state, _ = SyncState.objects.get_or_create(id=1)
    return JsonResponse({
        'last_run_at': state.last_run_at.isoformat() if state.last_run_at else None,
        'last_status': state.last_status,
        'last_error': state.last_error,
        'devices_synced_at': state.devices_synced_at.isoformat() if state.devices_synced_at else None,
        'collections_synced_until': state.collections_synced_until.isoformat() if state.collections_synced_until else None,
        'devices_count': Device.objects.filter(is_active=True).count(),
        'collections_count': Collection.objects.count(),
    })


# ─ 수정 이력 ───────────────────────────────────

@require_GET
def edit_logs(request):
    if not _is_admin(request):
        return JsonResponse({'error': '관리자 로그인 필요'}, status=403)
    limit = min(int(request.GET.get('limit') or 200), 1000)
    table = request.GET.get('table')
    row_id = request.GET.get('row_id')
    qs = EditLog.objects.all()
    if table:
        qs = qs.filter(table=table)
    if row_id:
        qs = qs.filter(row_id=int(row_id))
    items = [
        {
            'id': e.id, 'table': e.table, 'row_id': e.row_id, 'field': e.field,
            'old_value': e.old_value, 'new_value': e.new_value,
            'edited_by': e.edited_by, 'edited_at': e.edited_at.isoformat(),
        }
        for e in qs.order_by('-edited_at')[:limit]
    ]
    return JsonResponse({'count': len(items), 'items': items})
