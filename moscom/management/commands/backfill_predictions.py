"""과거 실측 데이터로 예측을 재현(backfill)해서 PredictionLog 에 채운다.

각 날짜 D에 대해, D 이전 실측만 사용해 D+1 / D+2 / D+3 을 예측(데이터 누출 없음).
이후 실측과 대조해 오차까지 계산한다.

사용:
  python manage.py backfill_predictions            # 전체 기간
  python manage.py backfill_predictions --days 30  # 최근 30일만
  python manage.py backfill_predictions --clear    # 기존 backfill 삭제 후 재생성
"""
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Sum

KST = timezone(timedelta(hours=9))
MAX_HORIZON = 3  # 1~3일 후 예측


class Command(BaseCommand):
    help = '과거 실측으로 예측을 재현해 PredictionLog 를 채웁니다.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=0, help='최근 N일만 (0=전체)')
        parser.add_argument('--clear', action='store_true', help='기존 backfill 행 삭제 후 재생성')

    def handle(self, *args, **opts):
        from moscom.models import Collection, Device, Region, PredictionLog
        from core import predictor

        if opts['clear']:
            n, _ = PredictionLog.objects.filter(model_version='backfill').delete()
            self.stdout.write(f'기존 backfill {n}행 삭제')

        # 1) 장비 메타
        regions = {r.code: r.name for r in Region.objects.all()}
        devices = {}
        for d in Device.objects.filter(is_active=True):
            devices[d.device_uuid] = {
                'name': (d.device_name or d.device_uuid),
                'region_name': regions.get(d.region_code, d.region_code) or '미지정',
                'region_code': d.region_code or '',
                'sido': d.address_sido or '',
            }
        if not devices:
            self.stdout.write(self.style.ERROR('활성 장비가 없습니다'))
            return

        # 2) 일별 실측 집계 (KST 기준)
        self.stdout.write('실측 집계 중…')
        daily = defaultdict(dict)   # uuid -> {date_str: count}
        qs = Collection.objects.filter(device_uuid__in=list(devices.keys())).values(
            'device_uuid', 'created_date', 'mosquito_count')
        for row in qs.iterator(chunk_size=5000):
            u = row['device_uuid']
            d_kst = row['created_date'].astimezone(KST).date().isoformat()
            daily[u][d_kst] = daily[u].get(d_kst, 0) + (row['mosquito_count'] or 0)

        all_dates = sorted({d for m in daily.values() for d in m.keys()})
        if not all_dates:
            self.stdout.write(self.style.ERROR('실측 데이터가 없습니다'))
            return
        if opts['days']:
            all_dates = all_dates[-opts['days']:]
        self.stdout.write(f'대상 기간: {all_dates[0]} ~ {all_dates[-1]} ({len(all_dates)}일), 장비 {len(devices)}대')

        # 3) 날짜별로 backcast 실행
        created = skipped = 0
        date_objs = [datetime.strptime(s, '%Y-%m-%d').date() for s in all_dates]
        date_set = set(all_dates)

        for i, snap in enumerate(date_objs):
            # snap 시점까지의 history 로 snap+1 ~ snap+3 예측
            targets = [snap + timedelta(days=h) for h in range(1, MAX_HORIZON + 1)]
            targets = [t for t in targets if t.isoformat() in date_set]  # 실측 있는 날만
            if not targets:
                continue

            batch = []
            for u, meta in devices.items():
                dmap = daily.get(u) or {}
                # snap 이하의 실측만 (누출 방지)
                hist = [{'date': ds, 'count': dmap[ds]} for ds in all_dates
                        if ds <= snap.isoformat() and ds in dmap]
                if len(hist) < 4:
                    continue
                for td in targets:
                    pred = predictor.backcast_for_date(
                        hist, td, region_code=meta['region_code'], sido=meta['sido'], weather={})
                    if pred is None:
                        continue
                    actual = dmap.get(td.isoformat())
                    counts = [h['count'] for h in hist]
                    err = (actual - pred) if actual is not None else None
                    batch.append(PredictionLog(
                        device_uuid=u, device_name=meta['name'], region_name=meta['region_name'],
                        snapshot_date=snap, target_date=td, horizon_days=(td - snap).days,
                        predicted=pred, predicted_raw=pred, predicted_index=None, grade='',
                        remedy_factor=1.0,
                        lag1=counts[-1] if counts else 0,
                        lag7=counts[-7] if len(counts) >= 7 else (counts[0] if counts else 0),
                        ma3=round(sum(counts[-3:]) / min(3, len(counts)), 1),
                        ma7=round(sum(counts[-7:]) / min(7, len(counts)), 1),
                        actual=actual,
                        error=err,
                        abs_error_pct=(round(abs(err) / max(1, actual) * 100, 1)
                                       if (actual is not None and err is not None) else None),
                        matched_at=(datetime.now(timezone.utc) if actual is not None else None),
                        model_version='backfill',
                    ))
            if batch:
                objs = PredictionLog.objects.bulk_create(batch, ignore_conflicts=True)
                created += len(batch)
            if (i + 1) % 10 == 0:
                self.stdout.write(f'  {i+1}/{len(date_objs)}일 처리… 누적 {created}행')

        total = PredictionLog.objects.count()
        matched = PredictionLog.objects.filter(actual__isnull=False).count()
        self.stdout.write(self.style.SUCCESS(
            f'완료 — 생성 시도 {created}행 · 전체 {total}행 · 실측 대조됨 {matched}행'))
