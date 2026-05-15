"""MOSCOM → 로컬 DB 동기화 서비스.

핵심 함수:
- sync_devices(): /device/listAll 호출 → Device 테이블 upsert
- sync_collections(since=None, until=None): /device/statisticsByDate raw → Collection upsert
- run_sync(): 두 개 다 + SyncState 갱신 (1시간 주기 호출용)
- backfill_collections(days=30): 최초 30일 백필
"""
import logging
from datetime import datetime, timedelta, timezone as dt_timezone

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core import moscom_client
from .models import Device, Collection, SyncState

logger = logging.getLogger(__name__)


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
    n_create = n_update = 0
    with transaction.atomic():
        for entry in raw:
            d = entry.get('device') or {}
            uuid = d.get('device_uuid') or entry.get('device_uuid')
            if not uuid:
                continue
            seen_uuids.add(uuid)
            setting = d.get('deviceSetting') or {}

            defaults = {
                'device_id': d.get('id'),
                'device_name': (d.get('device_name') or '').strip()[:200],
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
            }
            _, created = Device.objects.update_or_create(device_uuid=uuid, defaults=defaults)
            if created:
                n_create += 1
            else:
                n_update += 1

        # MOSCOM에서 빠진 장비는 비활성으로 표시 (삭제는 안 함 — Collection 참조 깨질 위험)
        Device.objects.exclude(device_uuid__in=seen_uuids).update(is_active=False)

    logger.info(f'sync_devices: created={n_create}, updated={n_update}, total={len(seen_uuids)}')
    return {'created': n_create, 'updated': n_update, 'total': len(seen_uuids)}


# ─ 포집 데이터 동기화 ───────────────────────────

def _fmt_dt(dt):
    """MOSCOM API 가 받는 형식: 'YYYY-MM-DDTHH:MM:SS' (no Z)."""
    if timezone.is_aware(dt):
        dt = dt.astimezone(dt_timezone.utc).replace(tzinfo=None)
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def _ingest_raw_batch(records):
    """raw 응답 리스트 → Collection 행 일괄 ingest. 중복(이미 있는 moscom_id) 자동 스킵."""
    if not records:
        return {'created': 0, 'skipped': 0}
    # 기존 moscom_id set
    incoming_ids = [r.get('id') for r in records if r.get('id') is not None]
    existing = set(
        Collection.objects.filter(moscom_id__in=incoming_ids).values_list('moscom_id', flat=True)
    )
    rows = []
    for r in records:
        mid = r.get('id')
        if mid is None or mid in existing:
            continue
        cd = _parse_iso(r.get('created_date'))
        if cd is None:
            continue
        rows.append(Collection(
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
    if rows:
        Collection.objects.bulk_create(rows, batch_size=500, ignore_conflicts=True)
    return {'created': len(rows), 'skipped': len(records) - len(rows)}


def sync_collections(since=None, until=None):
    """[since, until] 기간 raw 포집 동기화.
    since 없으면 SyncState.collections_synced_until (또는 24h 전).
    until 없으면 now.
    """
    state = _get_state()
    now = timezone.now()
    if until is None:
        until = now
    if since is None:
        since = state.collections_synced_until or (now - timedelta(hours=24))

    # 안전: 최소 60초 오버랩 (시간 경계 누락 방지)
    since = since - timedelta(seconds=60)
    if since >= until:
        return {'created': 0, 'skipped': 0, 'since': since.isoformat(), 'until': until.isoformat()}

    data = moscom_client.get_statistics_by_date(
        start_dt=_fmt_dt(since), end_dt=_fmt_dt(until),
        aggregation='raw', device_uuid='0', force_refresh=True,
    )
    if not isinstance(data, list):
        raise RuntimeError(f'unexpected raw response: {type(data).__name__}')
    result = _ingest_raw_batch(data)

    state.collections_synced_until = until
    state.save(update_fields=['collections_synced_until'])
    result['since'] = since.isoformat()
    result['until'] = until.isoformat()
    logger.info(f'sync_collections: {result}')
    return result


def backfill_collections(days=30, chunk_days=7):
    """과거 N일 백필. MOSCOM API가 한 번에 너무 큰 범위면 부담이 되니 chunk 로 쪼갬."""
    now = timezone.now()
    start = now - timedelta(days=days)
    total = {'created': 0, 'skipped': 0, 'chunks': 0}
    cur = start
    while cur < now:
        nxt = min(cur + timedelta(days=chunk_days), now)
        data = moscom_client.get_statistics_by_date(
            start_dt=_fmt_dt(cur), end_dt=_fmt_dt(nxt),
            aggregation='raw', device_uuid='0', force_refresh=True,
        )
        if isinstance(data, list):
            r = _ingest_raw_batch(data)
            total['created'] += r['created']
            total['skipped'] += r['skipped']
            total['chunks'] += 1
            logger.info(f'backfill chunk {cur} ~ {nxt}: {r}')
        cur = nxt

    state = _get_state()
    state.collections_synced_until = now
    state.save(update_fields=['collections_synced_until'])
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
