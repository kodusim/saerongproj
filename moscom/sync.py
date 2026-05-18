"""MOSCOM → 로컬 DB 동기화 서비스.

핵심 함수:
- sync_devices(): /device/listAll 호출 → Device 테이블 upsert
- sync_collections(since=None, until=None): /device/statisticsByDate raw → Collection upsert
- run_sync(): 두 개 다 + SyncState 갱신 (1시간 주기 호출용)
- backfill_collections(days=30): 최초 30일 백필
"""
import logging
import re
from datetime import datetime, timedelta, timezone as dt_timezone

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core import moscom_client
from .models import Device, Collection, SyncState, Region

logger = logging.getLogger(__name__)


# device_name 앞 prefix 추출. 알파벳 또는 한글 1글자 이상 + 선택적 후행 한글(예: "GH서").
# 매칭 안 되면 빈 문자열 ('' = 권역 미지정 = 천안 본사처럼 prefix 없는 그룹)
_PREFIX_RE = re.compile(r'^([A-Z]+(?:[가-힣]+)?|[가-힣]+)(?=\d|\s|$)')


def extract_region_code(device_name):
    """device_name 에서 권역 prefix 추출.
    예: 'KH02함박공원0029' → 'KH'
        'GH서01젤미공원0022' → 'GH서'
        'HA023.1절기념체육관0015' → 'HA'
        '260001sugwang' → ''
        '베트남 sugwang' → '베트남'
    """
    if not device_name:
        return ''
    name = device_name.strip()
    # 숫자로 시작하는 일련번호형은 prefix 없음
    if re.match(r'^\d', name):
        return ''
    m = _PREFIX_RE.match(name)
    return m.group(1) if m else ''


def _get_state():
    state, _ = SyncState.objects.get_or_create(id=1)
    return state


def _parse_iso(s):
    """MOSCOM 응답의 ISO datetime 문자열 파싱."""
    if not s:
        return None
    dt = parse_datetime(s)
    if dt and timezone.is_naive(dt):
        dt = dt.replace(tzinfo=dt_timezone.utc)
    return dt


# ─ 장비 동기화 ──────────────────────────────────

def sync_devices():
    """전체 장비 동기화. listAll은 가벼우니 매번 전체 upsert."""
    raw = moscom_client.list_devices(force_refresh=True)
    if not isinstance(raw, list):
        raise RuntimeError(f'unexpected list_devices response: {type(raw).__name__}')

    seen_uuids = set()
    seen_prefixes = set()
    n_create = n_update = 0
    with transaction.atomic():
        for entry in raw:
            d = entry.get('device') or {}
            uuid = d.get('device_uuid') or entry.get('device_uuid')
            if not uuid:
                continue
            seen_uuids.add(uuid)
            setting = d.get('deviceSetting') or {}
            dev_name = (d.get('device_name') or '').strip()[:200]
            region_code = extract_region_code(dev_name)[:20]
            if region_code:
                seen_prefixes.add(region_code)

            defaults = {
                'device_id': d.get('id'),
                'device_name': dev_name,
                'device_usim': (d.get('device_usim') or '')[:64],
                'address_sido': (d.get('address_sido') or '')[:50],
                'address_gungu': (d.get('address_gungu') or '')[:50],
                'address_dong': (d.get('address_dong') or '')[:50],
                'address_detail': (d.get('address_detail') or '')[:200],
                'latitude': float(d.get('latitude') or 0),
                'longitude': float(d.get('longitude') or 0),
                'mode': int(d.get('mode') or 0),
                'on_time': (d.get('on_time') or '')[:50],
                'co2_on_time': (d.get('co2_on_time') or '')[:50],
                'co2_period': int(d.get('co2_period') or 0),
                'current_mosquito_count': int(d.get('mosquito_count') or 0),
                'current_battery': int(d.get('battery') or 0),
                'current_charge': int(d.get('charge') or 0),
                'current_fan': int(d.get('fan') or 0),
                'device_date': _parse_iso(d.get('device_date')),
                'updated_date': _parse_iso(d.get('updated_date')),
                'created_date': _parse_iso(d.get('created_date')),
                'last_offline_alert_date': _parse_iso(d.get('last_offline_alert_date')),
                'last_battery_alert_date': _parse_iso(d.get('last_battery_alert_date')),
                'last_collection_alert_date': _parse_iso(d.get('last_collection_alert_date')),
                'normal_min': int(setting.get('normal_min', 0) or 0),
                'normal_max': int(setting.get('normal_max', 49) or 49),
                'warning_min': int(setting.get('warning_min', 50) or 50),
                'warning_max': int(setting.get('warning_max', 99) or 99),
                'bad_min': int(setting.get('bad_min', 100) or 100),
                'bad_max': int(setting.get('bad_max', 10000) or 10000),
                'is_active': True,
                'region_code': region_code,
            }
            _, created = Device.objects.update_or_create(device_uuid=uuid, defaults=defaults)
            if created:
                n_create += 1
            else:
                n_update += 1

        # MOSCOM에서 빠진 장비는 비활성으로 표시 (삭제는 안 함 — Collection 참조 깨질 위험)
        Device.objects.exclude(device_uuid__in=seen_uuids).update(is_active=False)

        # 새로 발견된 prefix 는 Region 마스터에 자동 생성 (name=code 기본값, 관리자가 수정)
        existing = set(Region.objects.values_list('code', flat=True))
        for code in seen_prefixes:
            if code not in existing:
                Region.objects.create(code=code, name=code, sort_order=100)

    logger.info(f'sync_devices: created={n_create}, updated={n_update}, total={len(seen_uuids)}, prefixes={len(seen_prefixes)}')
    return {'created': n_create, 'updated': n_update, 'total': len(seen_uuids), 'prefixes': len(seen_prefixes)}


# ─ 포집 데이터 동기화 ───────────────────────────

def _fmt_dt(dt):
    """MOSCOM API 가 받는 형식: 'YYYY-MM-DDTHH:MM:SS' (no Z)."""
    if timezone.is_aware(dt):
        dt = dt.astimezone(dt_timezone.utc).replace(tzinfo=None)
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def _ingest_raw_batch(records, overwrite_edited=False):
    """raw 응답 리스트 → Collection 행 일괄 ingest.
    overwrite_edited=False (기본): 이미 있는 행 자체를 스킵 — 데이터 보존.
    overwrite_edited=True: 이미 있는 행의 값(mosquito_count 등) 을 새 응답값으로 덮어쓰기.
        edited=True 인 행도 강제 덮어씀 (수정 이력은 EditLog 에 남아있음).
    """
    if not records:
        return {'created': 0, 'updated': 0, 'skipped': 0}

    incoming_ids = [r.get('id') for r in records if r.get('id') is not None]
    existing_map = {
        c.moscom_id: c for c in
        Collection.objects.filter(moscom_id__in=incoming_ids)
    }

    new_rows = []
    n_updated = 0
    n_skipped = 0
    for r in records:
        mid = r.get('id')
        if mid is None:
            continue
        cd = _parse_iso(r.get('created_date'))
        if cd is None:
            continue
        existing = existing_map.get(mid)
        if existing is not None:
            if not overwrite_edited:
                n_skipped += 1
                continue
            # 덮어쓰기 — edited 상태도 풀고 원본으로 복원
            existing.mosquito_count = int(r.get('mosquito_count') or 0)
            existing.reset = bool(r.get('reset'))
            existing.battery = int(r.get('battery') or 0)
            existing.charge = int(r.get('charge') or 0)
            existing.fan = int(r.get('fan') or 0)
            existing.created_date = cd
            existing.edited = False
            existing.save()
            n_updated += 1
            continue
        new_rows.append(Collection(
            moscom_id=mid,
            device_uuid=(r.get('device_uuid') or '')[:64],
            mosquito_count=int(r.get('mosquito_count') or 0),
            reset=bool(r.get('reset')),
            battery=int(r.get('battery') or 0),
            charge=int(r.get('charge') or 0),
            fan=int(r.get('fan') or 0),
            created_date=cd,
            edited=False,
        ))
    if new_rows:
        Collection.objects.bulk_create(new_rows, batch_size=500, ignore_conflicts=True)
    return {'created': len(new_rows), 'updated': n_updated, 'skipped': n_skipped}


def sync_collections(since=None, until=None, overwrite_edited=False):
    """[since, until] 기간 raw 포집 동기화."""
    state = _get_state()
    now = timezone.now()
    if until is None:
        until = now
    if since is None:
        since = state.collections_synced_until or (now - timedelta(hours=24))

    since = since - timedelta(seconds=60)
    if since >= until:
        return {'created': 0, 'updated': 0, 'skipped': 0, 'since': since.isoformat(), 'until': until.isoformat()}

    data = moscom_client.get_statistics_by_date(
        start_dt=_fmt_dt(since), end_dt=_fmt_dt(until),
        aggregation='raw', device_uuid='0', force_refresh=True,
    )
    if not isinstance(data, list):
        raise RuntimeError(f'unexpected raw response: {type(data).__name__}')
    result = _ingest_raw_batch(data, overwrite_edited=overwrite_edited)

    state.collections_synced_until = until
    state.save(update_fields=['collections_synced_until'])
    result['since'] = since.isoformat()
    result['until'] = until.isoformat()
    result['overwrite_edited'] = overwrite_edited
    logger.info(f'sync_collections: {result}')
    return result


def backfill_collections(days=30, chunk_days=7, overwrite_edited=False):
    """과거 N일 백필."""
    now = timezone.now()
    start = now - timedelta(days=days)
    total = {'created': 0, 'updated': 0, 'skipped': 0, 'chunks': 0}
    cur = start
    while cur < now:
        nxt = min(cur + timedelta(days=chunk_days), now)
        data = moscom_client.get_statistics_by_date(
            start_dt=_fmt_dt(cur), end_dt=_fmt_dt(nxt),
            aggregation='raw', device_uuid='0', force_refresh=True,
        )
        if isinstance(data, list):
            r = _ingest_raw_batch(data, overwrite_edited=overwrite_edited)
            total['created'] += r['created']
            total['updated'] += r.get('updated', 0)
            total['skipped'] += r['skipped']
            total['chunks'] += 1
            logger.info(f'backfill chunk {cur} ~ {nxt}: {r}')
        cur = nxt

    state = _get_state()
    state.collections_synced_until = now
    state.save(update_fields=['collections_synced_until'])
    total['overwrite_edited'] = overwrite_edited
    return total


# ─ 메인 진입점 ─────────────────────────────────

def run_sync():
    """Celery 가 1시간마다 호출. 장비 + 포집 incremental + 날씨."""
    state = _get_state()
    state.last_run_at = timezone.now()
    try:
        dr = sync_devices()
        cr = sync_collections()
        # 날씨 동기화 (실패해도 sync 전체 fail 시키지 않음)
        try:
            from .weather import sync_weather
            wr = sync_weather()
        except Exception as we:
            logger.warning(f'weather sync failed: {we}')
            wr = {'error': str(we)}
        state.last_status = 'ok'
        state.last_error = ''
        state.devices_synced_at = timezone.now()
        state.save(update_fields=['last_run_at', 'last_status', 'last_error', 'devices_synced_at'])
        return {'devices': dr, 'collections': cr, 'weather': wr}
    except Exception as e:
        logger.exception('run_sync failed')
        state.last_status = 'error'
        state.last_error = (str(e) or repr(e))[:1000]
        state.save(update_fields=['last_run_at', 'last_status', 'last_error'])
        raise
