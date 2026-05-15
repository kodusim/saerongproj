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

from .models import Device, Collection, SyncState, EditLog
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


# ─ 장비 ────────────────────────────────────────

@require_GET
def device_list(request):
    qs = Device.objects.filter(is_active=True)
    sido = request.GET.get('sido')
    if sido:
        qs = qs.filter(address_sido=sido)
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
            }
            for d in qs
        ],
    })


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
