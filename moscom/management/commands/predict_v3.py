"""version_3 모델로 매일 배치 예측 → PredictionLog 저장.

파이프라인:
  1) moscom 일별값(get_daily_map) + 장비상태(Collection)로 관측소×업무일 panel 생성
     (숫자이름 관측소 제외, 웹사이트/moscom.co.kr 과 동일한 일별값)
  2) 날씨 결합 + version_3 피처(119개) 생성
  3) best_h1/h2/h3 모델(delta_log)로 h=1~3 예측 복원
  4) 각 (관측소, 산출일, 대상일)을 PredictionLog 에 저장 (스냅샷 이력)

사용:
  python manage.py predict_v3               # 오늘 기준 예측 스냅샷 저장
  python manage.py predict_v3 --backfill    # 과거 전체를 재현해 이력 채움
"""
import os
import sys
import warnings
from datetime import datetime, timedelta, timezone, date as date_cls
from pathlib import Path

import numpy as np
import pandas as pd

from django.core.management.base import BaseCommand

warnings.filterwarnings("ignore")

KST = timezone(timedelta(hours=9))
V3_DIR = Path(__file__).resolve().parent.parent.parent / "predictor_v3"
V3_SRC = V3_DIR / "src"
V3_MODELS = V3_DIR / "models"
LAG_WINDOW = 7
HORIZONS = [1, 2, 3]

# 발육영점온도 등 version_3 피처 함수 import (src를 경로에 추가)
sys.path.insert(0, str(V3_SRC))


def _load_v3_feature_funcs():
    """03_features.py 의 함수들을 동적 로드 (파일명이 숫자로 시작해 import 불가)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("v3_features", str(V3_SRC / "03_features.py"))
    mod = importlib.util.module_from_spec(spec)
    # config 의존을 우회하기 위해 더미 config 주입
    _inject_dummy_config()
    spec.loader.exec_module(mod)
    return mod


def _inject_dummy_config():
    import types
    cfg = types.ModuleType("config")
    cfg.PANEL_CSV = None
    cfg.WEATHER_CSV = None
    cfg.FEATURES_CSV = None
    cfg.LAG_WINDOW = LAG_WINDOW
    cfg.HORIZONS = HORIZONS
    cfg.DATA_DIR = V3_DIR / "data"
    sys.modules["config"] = cfg


class Command(BaseCommand):
    help = "version_3 모델로 예측해 PredictionLog 에 저장"

    def add_arguments(self, parser):
        parser.add_argument('--backfill', action='store_true', help='과거 전체 재현')
        parser.add_argument('--days', type=int, default=0, help='최근 N일만(backfill)')

    def handle(self, *args, **opts):
        import joblib
        from core import moscom_client
        from moscom.models import Collection, Device, Region, PredictionLog
        from django.db.models import Min, Max

        # 모델 로드
        models = {}
        for h in HORIZONS:
            p = V3_MODELS / f"best_h{h}.joblib"
            if not p.exists():
                self.stderr.write(f'모델 없음: {p}'); return
            models[h] = joblib.load(p)
        self.stdout.write(f'모델 로드: h1={models[1]["name"]}, h2={models[2]["name"]}, h3={models[3]["name"]}')

        v3 = _load_v3_feature_funcs()

        # 1) panel 생성 (moscom 일별값 + 장비상태)
        self.stdout.write('panel 생성(moscom 일별값)…')
        panel = self._build_panel(moscom_client, Collection, Device, Region)
        if panel is None or panel.empty:
            self.stderr.write('panel 비어있음'); return
        self.stdout.write(f'  관측소 {panel["sid"].nunique()}개, {len(panel):,}행, '
                          f'{panel["bizdate"].min():%Y-%m-%d}~{panel["bizdate"].max():%Y-%m-%d}')

        # 2) 날씨 + 피처
        weather = self._build_weather(panel)
        df = self._build_features(v3, panel, weather)

        # 3) 예측 (delta_log 복원)
        snap_today = _business_yesterday()
        rows_out = []
        for h in HORIZONS:
            mdict = models[h]
            feats = mdict['features']
            mdl = mdict['model']
            d = df[df['y'].notna()].copy()
            # 학습에 쓰인 피처만, 없으면 0
            X = d.reindex(columns=feats, fill_value=0.0)
            base = np.log1p(d['y'].values.astype(float))
            pred = np.clip(np.expm1(base + mdl.predict(X)), 0, None)
            d = d.assign(_pred=np.round(pred).astype(int), _h=h)
            rows_out.append(d[['sid', 'station', 'region', 'bizdate', '_h', '_pred', 'y']])
        allp = pd.concat(rows_out, ignore_index=True)

        # 4) PredictionLog 저장
        if opts['backfill']:
            self._save_backfill(allp, panel, PredictionLog, opts.get('days') or 0)
        else:
            self._save_today(allp, panel, snap_today, PredictionLog)

    # ── panel: moscom 일별값 + 장비상태 ──
    def _build_panel(self, moscom_client, Collection, Device, Region):
        rng = Collection.objects.aggregate(mn=Min('created_date'), mx=Max('created_date'))
        if not rng['mn']:
            return None
        d0 = rng['mn'].astimezone(KST).date()
        d1 = rng['mx'].astimezone(KST).date()
        regions = {r.code: r.name for r in Region.objects.all()}
        dev = {d.device_uuid: {
            'name': (d.device_name or d.device_uuid),
            'region': (d.address_sido or '') + ((' ' + d.address_gungu) if d.address_gungu else '') or '미지정',
        } for d in Device.objects.all()}

        # moscom 일별 y
        dmap = moscom_client.get_daily_map(d0, d1)
        recs = []
        for u, per in dmap.items():
            m = dev.get(u)
            if not m:
                continue
            nm = m['name']
            if str(nm).isdigit():   # 숫자이름 관측소 제외
                continue
            for ds, cnt in per.items():
                recs.append({'sid': nm, 'station': nm, 'device': nm,
                             'region': m['region'], 'bizdate': ds, 'y': cnt})
        if not recs:
            return None
        panel = pd.DataFrame(recs)
        panel['bizdate'] = pd.to_datetime(panel['bizdate'])

        # 장비상태(fan_hours, n_meas, battery, peak_hour) — Collection raw 로 야간창 집계
        state = self._device_state(Collection, dev)
        panel = panel.merge(state, on=['sid', 'bizdate'], how='left')
        for c, dflt in (('n_meas', 12), ('fan_hours', 0), ('battery', 50),
                        ('n_reset', 0), ('peak_hour', -1)):
            if c not in panel:
                panel[c] = dflt
            panel[c] = panel[c].fillna(dflt)

        # 결측 날짜 채우기 (관측소별 연속 날짜)
        frames = []
        for sid, gg in panel.groupby('sid', sort=False):
            gg = gg.sort_values('bizdate').set_index('bizdate')
            full = pd.date_range(gg.index.min(), gg.index.max(), freq='D')
            gg = gg.reindex(full)
            gg.index.name = 'bizdate'
            for c in ('sid', 'station', 'device', 'region'):
                gg[c] = gg[c].ffill().bfill()
            frames.append(gg.reset_index())
        panel = pd.concat(frames, ignore_index=True)
        panel['is_missing'] = panel['y'].isna().astype(int)
        panel['device_off'] = ((panel['fan_hours'].fillna(0) == 0) & (panel['y'].fillna(0) == 0)).astype(int)
        panel = panel.sort_values(['sid', 'bizdate']).reset_index(drop=True)
        obs = panel.groupby('sid')['y'].apply(lambda s: s.notna().sum())
        panel['n_obs_days'] = panel['sid'].map(obs)
        return panel

    def _device_state(self, Collection, dev):
        """야간 수집창 기준 장비상태 일별 집계."""
        name_by_uuid = {u: m['name'] for u, m in dev.items()}
        qs = Collection.objects.values('device_uuid', 'created_date', 'battery', 'fan', 'reset')
        rows = []
        for r in qs.iterator(chunk_size=5000):
            nm = name_by_uuid.get(r['device_uuid'])
            if not nm or str(nm).isdigit():
                continue
            t = r['created_date'].astimezone(KST)
            h = t.hour
            if not (h >= 18 or h <= 5):
                continue
            biz = t.date() if h >= 18 else (t.date() - timedelta(days=1))
            rows.append((nm, biz, r['battery'] or 0, 1 if r['fan'] else 0, 1 if r['reset'] else 0, h))
        if not rows:
            return pd.DataFrame(columns=['sid', 'bizdate', 'n_meas', 'fan_hours', 'battery', 'n_reset', 'peak_hour'])
        s = pd.DataFrame(rows, columns=['sid', 'biz', 'battery', 'fan', 'reset', 'hour'])
        g = s.groupby(['sid', 'biz']).agg(
            n_meas=('fan', 'size'), fan_hours=('fan', 'sum'),
            battery=('battery', 'mean'), n_reset=('reset', 'sum')).reset_index()
        g['peak_hour'] = -1
        g = g.rename(columns={'biz': 'bizdate'})
        g['bizdate'] = pd.to_datetime(g['bizdate'])
        return g

    def _build_weather(self, panel):
        # 서버엔 실시간 날씨 API가 없으니, Device 캐시 날씨를 권역별 평균으로 상수 사용.
        # (version_3 는 open-meteo 를 썼으나 배치 단순화. 날씨 피처는 상수로 채워짐)
        from moscom.models import Device
        wcols = ['temperature_2m_mean', 'temperature_2m_max', 'temperature_2m_min',
                 'precipitation_sum', 'night_temp', 'night_temp_min',
                 'night_humid', 'night_precip', 'night_wind']
        reg_w = {}
        for d in Device.objects.all():
            reg = (d.address_sido or '') + ((' ' + d.address_gungu) if d.address_gungu else '') or '미지정'
            reg_w.setdefault(reg, []).append((d.temperature, d.humidity, d.precipitation, d.wind_speed))
        dates = pd.date_range(panel['bizdate'].min(), panel['bizdate'].max(), freq='D')
        recs = []
        for reg, vals in reg_w.items():
            t = np.nanmean([v[0] for v in vals if v[0] is not None]) if any(v[0] is not None for v in vals) else 22.0
            hu = np.nanmean([v[1] for v in vals if v[1] is not None]) if any(v[1] is not None for v in vals) else 60.0
            pr = np.nanmean([v[2] for v in vals if v[2] is not None]) if any(v[2] is not None for v in vals) else 0.0
            wi = np.nanmean([v[3] for v in vals if v[3] is not None]) if any(v[3] is not None for v in vals) else 2.0
            for dt in dates:
                recs.append({'region': reg, 'date': dt,
                             'temperature_2m_mean': t, 'temperature_2m_max': t + 4, 'temperature_2m_min': t - 4,
                             'precipitation_sum': pr, 'night_temp': t - 2, 'night_temp_min': t - 5,
                             'night_humid': hu, 'night_precip': pr, 'night_wind': wi})
        return pd.DataFrame(recs)

    def _build_features(self, v3, panel, weather):
        weather = weather.sort_values(['region', 'date'])
        weather = pd.concat([v3.add_weather_lags(g.copy()) for _, g in weather.groupby('region', sort=False)],
                            ignore_index=True)
        wcols = [c for c in weather.columns if c.startswith('w_')]
        weather = weather[['region', 'date'] + wcols]

        panel = panel.sort_values(['sid', 'bizdate'])
        panel = pd.concat([v3.add_target_lags(g.copy()) for _, g in panel.groupby('sid', sort=False)],
                          ignore_index=True)
        df = panel.merge(weather, left_on=['region', 'bizdate'], right_on=['region', 'date'], how='left')
        if 'date' in df:
            df = df.drop(columns='date')
        df = v3.add_cross_section(df)
        # 달력 피처(예측 대상일 기준) + 코드
        for h in HORIZONS:
            td = df['bizdate'] + pd.Timedelta(days=h)
            df[f'dow_h{h}'] = td.dt.dayofweek
            df[f'month_h{h}'] = td.dt.month
            df[f'doy_h{h}'] = td.dt.dayofyear
            df[f'is_weekend_h{h}'] = (td.dt.dayofweek >= 5).astype(int)
        df['sid_code'] = df['sid'].astype('category').cat.codes
        df['region_code'] = df['region'].astype('category').cat.codes
        ylog = np.log1p(df['y'])
        df['sid_expmean'] = (ylog.groupby(df['sid']).apply(
            lambda s: s.shift(1).expanding(min_periods=3).mean()).reset_index(level=0, drop=True))
        return df

    def _save_today(self, allp, panel, snap, PredictionLog):
        # 기준일(snap)에서 만든 h=1~3 예측을 저장
        created = 0
        reg_by_sid = dict(zip(panel['station'], panel['region']))
        for _, r in allp.iterrows():
            if pd.to_datetime(r['bizdate']).date() != snap:
                continue
            td = snap + timedelta(days=int(r['_h']))
            _, c = PredictionLog.objects.get_or_create(
                device_uuid=r['sid'], snapshot_date=snap, target_date=td,
                defaults=dict(device_name=r['station'], region_name=reg_by_sid.get(r['sid'], ''),
                              horizon_days=int(r['_h']), predicted=int(r['_pred']),
                              predicted_raw=int(r['_pred']), model_version='v3'))
            created += int(c)
        self.stdout.write(self.style.SUCCESS(f'오늘({snap}) 예측 저장: {created}행'))
        # 실측 대조
        from core import prediction_log as plog
        u = plog.match_actuals()
        self.stdout.write(f'실측 대조: {u}행')

    def _save_backfill(self, allp, panel, PredictionLog, days):
        # 각 기준일마다 그날 만든 h=1~3 예측을 이력으로 저장 (과거 예측 재현)
        # 구 모델(backfill/v2)이 unique 제약을 선점하지 않도록 함께 제거하고 v3로 대체
        PredictionLog.objects.filter(model_version__in=['v3', 'backfill', 'v2']).delete()
        reg_by_sid = dict(zip(panel['station'], panel['region']))
        y_by = {(r['station'], pd.to_datetime(r['bizdate']).date()): r['y']
                for _, r in panel.iterrows() if pd.notna(r['y'])}
        objs = []
        dmax = allp['bizdate'].max()
        for _, r in allp.iterrows():
            snap = pd.to_datetime(r['bizdate']).date()
            if days and (dmax.date() - snap).days > days:
                continue
            td = snap + timedelta(days=int(r['_h']))
            actual = y_by.get((r['station'], td))
            err = (int(actual) - int(r['_pred'])) if actual is not None else None
            objs.append(PredictionLog(
                device_uuid=r['sid'], device_name=r['station'],
                region_name=reg_by_sid.get(r['sid'], ''),
                snapshot_date=snap, target_date=td, horizon_days=int(r['_h']),
                predicted=int(r['_pred']), predicted_raw=int(r['_pred']),
                actual=(int(actual) if actual is not None else None),
                error=err,
                abs_error_pct=(round(abs(err) / max(1, int(actual)) * 100, 1)
                               if (actual is not None and err is not None) else None),
                matched_at=(datetime.now(timezone.utc) if actual is not None else None),
                model_version='v3'))
        PredictionLog.objects.bulk_create(objs, ignore_conflicts=True, batch_size=2000)
        self.stdout.write(self.style.SUCCESS(f'backfill 저장: {len(objs)}행'))


def _business_yesterday():
    try:
        from moscom.timeutil import business_yesterday
        return business_yesterday()
    except Exception:
        return (datetime.now(KST).date() - timedelta(days=1))
