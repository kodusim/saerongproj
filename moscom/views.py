"""moscom DB 기반 조회 + 수정 API.

조회: 누구나 (기존 mosquito-test 처럼)
수정: 관리자만 (request.session 의 'mosquito_admin' 또는 staff)
"""
import json
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from django.views.decorators.http import require_GET, require_http_methods
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
    params: start, end (YYYY-MM-DD), unit (day|week|month|year), device_uuid?, region_code?
    """
    from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
    from django.db.models import Sum, Count, Avg, Max as DbMax, Min as DbMin
    from datetime import datetime as dt

    unit = (request.GET.get('unit') or 'day').strip().lower()
    if unit not in ('day', 'week', 'month', 'year'):
        return JsonResponse({'error': 'unit must be day|week|month|year'}, status=400)

    start_s = request.GET.get('start')
    end_s = request.GET.get('end')
    try:
        start = dt.fromisoformat(start_s) if start_s else None
        end = dt.fromisoformat(end_s) if end_s else None
    except ValueError:
        return JsonResponse({'error': 'date format YYYY-MM-DD'}, status=400)

    qs = Collection.objects.all()
    if start:
        qs = qs.filter(created_date__gte=timezone.make_aware(dt.combine(start, dt.min.time())))
    if end:
        qs = qs.filter(created_date__lte=timezone.make_aware(dt.combine(end, dt.max.time())))
    device_uuid = request.GET.get('device_uuid')
    if device_uuid:
        qs = qs.filter(device_uuid=device_uuid)

    # 권역 필터 (Device.region_code 매칭)
    region_code = request.GET.get('region_code')
    if region_code is not None:
        dev_uuids = list(
            Device.objects.filter(region_code=region_code, is_active=True)
            .values_list('device_uuid', flat=True)
        )
        qs = qs.filter(device_uuid__in=dev_uuids)

    trunc = {
        'day': TruncDate('created_date'),
        'week': TruncWeek('created_date'),
        'month': TruncMonth('created_date'),
        'year': TruncYear('created_date'),
    }[unit]
    rows = list(
        qs.annotate(bucket=trunc)
          .values('bucket', 'device_uuid')
          .annotate(
              total=Sum('mosquito_count'),
              events=Count('id'),
              avg=Avg('mosquito_count'),
              max=DbMax('mosquito_count'),
          )
          .order_by('bucket', 'device_uuid')
    )

    # 장비 메타
    devices = {d.device_uuid: d for d in Device.objects.all()}
    region_name_by_code = {r.code: r.name for r in Region.objects.all()}

    items = []
    for r in rows:
        d = devices.get(r['device_uuid'])
        bucket = r['bucket']
        items.append({
            'bucket': bucket.isoformat() if hasattr(bucket, 'isoformat') else str(bucket),
            'device_uuid': r['device_uuid'],
            'device_name': d.device_name if d else r['device_uuid'],
            'region_code': (d.region_code if d else '') or '',
            'region_name': region_name_by_code.get((d.region_code if d else ''), '미지정') if d else '미지정',
            'total': r['total'] or 0,
            'events': r['events'] or 0,
            'avg': round(r['avg'] or 0, 2),
            'max': r['max'] or 0,
        })

    # bucket 단위로 총합도 같이
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
                'region_name': region_map.get(d.region_code, d.region_code or '미지정'),
            }
            for d in qs
        ],
    })


@require_GET
def region_list(request):
    """권역 목록. 각 권역별 장비 수 포함."""
    from collections import Counter
    counts = Counter(Device.objects.filter(is_active=True).values_list('region_code', flat=True))
    regions = list(Region.objects.all())
    # DB 에 없지만 Device 에 prefix 있는 경우 — 빈 row 도 노출
    existing_codes = {r.code for r in regions}
    extra_codes = sorted(set(counts.keys()) - existing_codes - {''})
    return JsonResponse({
        'items': [
            {
                'id': r.id, 'code': r.code, 'name': r.name,
                'sort_order': r.sort_order, 'note': r.note,
                'device_count': counts.get(r.code, 0),
            }
            for r in regions
        ] + [
            # Region 마스터에 없지만 Device 에는 prefix 있는 경우 (lazy)
            {'id': None, 'code': c, 'name': c, 'sort_order': 100, 'note': '',
             'device_count': counts.get(c, 0)}
            for c in extra_codes
        ],
        'unassigned_device_count': counts.get('', 0),
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
    for k in ['name', 'sort_order', 'note']:
        if k in body:
            old = getattr(r, k)
            new = body[k]
            if k == 'sort_order':
                try: new = int(new)
                except (TypeError, ValueError): continue
            if k in ('name', 'note'):
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
                'normal_max', 'warning_max', 'bad_min']
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
