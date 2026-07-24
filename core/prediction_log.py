"""AI 예측 로그 — 예측 스냅샷 누적 + 실측 대조(정확도 검증).

목적: 예측은 매일 바뀌므로 "그때 그 예측"을 보관해 두고,
      나중에 실측이 들어오면 비교해서 모델 정확도를 추적한다.

- save_snapshot(preds, meta_by_uuid): 오늘자 예측을 PredictionLog 에 저장 (하루 1회, 중복 무시)
- match_actuals(): 실측이 들어온 target_date 행에 actual/error 채우기
- accuracy_summary(): 예측 간격(며칠 뒤 예측인지)별 정확도 요약
"""
import logging
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


def _today_kst():
    try:
        from moscom.timeutil import business_today
        return business_today()
    except Exception:
        return datetime.now(KST).date()


def save_snapshot(preds, meta_by_uuid=None, snapshot_date=None):
    """예측 결과(preds: moscom_predict 의 predictions 배열)를 스냅샷 저장.
    같은 (device, snapshot_date, target_date) 는 중복 저장하지 않음(unique 제약).
    반환: (created_count, skipped_count)
    """
    from moscom.models import PredictionLog
    meta_by_uuid = meta_by_uuid or {}
    snap = snapshot_date or _today_kst()
    created = skipped = 0

    for p in (preds or []):
        uuid = p.get('uuid')
        if not uuid:
            continue
        m = meta_by_uuid.get(uuid, {})
        hist = p.get('history') or []
        counts = [h.get('count', 0) for h in hist]
        lag1 = counts[-1] if counts else 0
        lag7 = counts[-7] if len(counts) >= 7 else (counts[0] if counts else 0)
        ma3 = round(sum(counts[-3:]) / min(3, len(counts)), 1) if counts else 0
        ma7 = round(sum(counts[-7:]) / min(7, len(counts)), 1) if counts else 0
        w = m.get('weather') or {}

        for pp in (p.get('predictions') or []):
            tds = pp.get('date')
            if not tds:
                continue
            try:
                td = datetime.strptime(tds[:10], '%Y-%m-%d').date()
            except Exception:
                continue
            try:
                _, was_created = PredictionLog.objects.get_or_create(
                    device_uuid=uuid, snapshot_date=snap, target_date=td,
                    defaults={
                        'device_name': p.get('name') or '',
                        'region_name': m.get('region_name') or p.get('region') or '',
                        'horizon_days': (td - snap).days,
                        'predicted': pp.get('predicted') or 0,
                        'predicted_raw': pp.get('predicted_raw') or pp.get('predicted') or 0,
                        'predicted_index': pp.get('predicted_index'),
                        'grade': pp.get('grade') or '',
                        'remedy_factor': pp.get('remedy_factor') or 1.0,
                        'lag1': lag1, 'lag7': lag7, 'ma3': ma3, 'ma7': ma7,
                        'temperature': w.get('temperature'),
                        'humidity': w.get('humidity'),
                        'precipitation': w.get('precipitation'),
                        'wind_speed': w.get('wind_speed'),
                        'model_version': (m.get('model_version') or 'v2'),
                    },
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1
            except Exception:
                logger.exception('prediction snapshot save failed: %s %s', uuid, td)
    return created, skipped


def match_actuals(daily_by_uuid=None, limit_days=400):
    """실측이 확보된 과거 예측 행에 actual/error 채우기.
    daily_by_uuid: {uuid: {'YYYY-MM-DD': count}} 형태(선택). 없으면 Collection 에서 집계.
    반환: 갱신된 행 수
    """
    from moscom.models import PredictionLog
    today = _today_kst()
    since = today - timedelta(days=limit_days)
    # 아직 대조 안 됐고, 대상일이 이미 지난(=실측 확보 가능) 행
    qs = PredictionLog.objects.filter(actual__isnull=True, target_date__lt=today, target_date__gte=since)
    updated = 0
    cache = {}

    for row in qs.iterator():
        u, td = row.device_uuid, row.target_date
        tds = td.isoformat()
        actual = None
        if daily_by_uuid and u in daily_by_uuid:
            actual = daily_by_uuid[u].get(tds)
        if actual is None:
            key = (u, tds)
            if key in cache:
                actual = cache[key]
            else:
                actual = _actual_from_db(u, td)
                cache[key] = actual
        if actual is None:
            continue
        row.actual = int(actual)
        row.error = int(actual) - (row.predicted or 0)
        base = max(1, int(actual))
        row.abs_error_pct = round(abs(row.error) / base * 100, 1)
        row.matched_at = datetime.now(timezone.utc)
        try:
            row.save(update_fields=['actual', 'error', 'abs_error_pct', 'matched_at'])
            updated += 1
        except Exception:
            logger.exception('actual match save failed: %s %s', u, td)
    return updated


def _actual_from_db(device_uuid, target_date):
    """Collection 에서 해당 장비·날짜(KST)의 포집 합계."""
    try:
        from django.db.models import Sum
        from moscom.models import Collection
        start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=KST)
        end = start + timedelta(days=1)
        agg = Collection.objects.filter(
            device_uuid=device_uuid,
            created_date__gte=start.astimezone(timezone.utc),
            created_date__lt=end.astimezone(timezone.utc),
        ).aggregate(t=Sum('mosquito_count'))
        return agg.get('t')
    except Exception:
        logger.exception('actual lookup failed')
        return None


def accuracy_summary(days=30, allowed_uuids=None):
    """예측 간격(며칠 뒤 예측인지)별 정확도 요약. 반환: {'overall': {...}, 'by_horizon': [...]}"""
    from moscom.models import PredictionLog
    today = _today_kst()
    since = today - timedelta(days=days)
    qs = PredictionLog.objects.filter(actual__isnull=False, target_date__gte=since)
    if allowed_uuids is not None:
        qs = qs.filter(device_uuid__in=list(allowed_uuids))

    rows = list(qs.values('horizon_days', 'predicted', 'actual', 'error', 'abs_error_pct'))
    if not rows:
        return {'overall': None, 'by_horizon': [], 'count': 0}

    def _agg(items):
        n = len(items)
        mae = sum(abs(r['error'] or 0) for r in items) / n
        mape = sum((r['abs_error_pct'] or 0) for r in items) / n
        bias = sum((r['error'] or 0) for r in items) / n
        # 오차 20% 이내 비율 (적중률)
        hit = sum(1 for r in items if (r['abs_error_pct'] or 999) <= 20) / n * 100
        return {
            'count': n,
            'mae': round(mae, 1),          # 평균 절대 오차(마리)
            'mape': round(mape, 1),        # 평균 절대 오차율(%)
            'bias': round(bias, 1),        # 편향(+면 과소예측)
            'hit_rate': round(hit, 1),     # 오차 20% 이내 비율
        }

    by_h = {}
    for r in rows:
        by_h.setdefault(r['horizon_days'], []).append(r)
    by_horizon = [{'horizon_days': h, **_agg(v)} for h, v in sorted(by_h.items())]
    return {'overall': _agg(rows), 'by_horizon': by_horizon, 'count': len(rows)}
