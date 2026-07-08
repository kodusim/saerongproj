"""AI 모기 발생 예측기 (재학습 모델 v2).

학습 데이터: moscom Collection (장비×일 집계) — manage.py moscom_train 으로 생성.
피처: lag1/2/3/7, ma3/ma7, weekday/is_weekend/month/day, region_code one-hot,
       (옵션) temperature/humidity/precipitation/wind_speed

predictor 는 multi-day 예측 시 첫 번째 날만 모델로 예측하고, 그 결과를
다음 날 lag1 로 넣어 재귀적으로 N일 예측 (recursive forecasting).
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 우선 moscom/ml 에서 찾고, 없으면 기존 core/ml 로 fallback
_PROJ_ROOT = os.path.dirname(os.path.dirname(__file__))
_NEW_ML_DIR = os.path.join(_PROJ_ROOT, 'moscom', 'ml')
_OLD_ML_DIR = os.path.join(os.path.dirname(__file__), 'ml')


def _model_paths():
    """새 모델 우선, 없으면 기존 모델."""
    new_model = os.path.join(_NEW_ML_DIR, 'best_model_RandomForest.joblib')
    new_feat = os.path.join(_NEW_ML_DIR, 'feature_cols.joblib')
    if os.path.exists(new_model) and os.path.exists(new_feat):
        return new_model, new_feat, 'v2'
    return (
        os.path.join(_OLD_ML_DIR, 'best_model_RandomForest.joblib'),
        os.path.join(_OLD_ML_DIR, 'feature_cols.joblib'),
        'v1',
    )


@lru_cache(maxsize=1)
def _load():
    import joblib
    mp, fp, ver = _model_paths()
    if not os.path.exists(mp):
        raise FileNotFoundError(f'model not found: {mp}')
    model = joblib.load(mp)
    feature_cols = joblib.load(fp)
    logger.info('AI model loaded (%s, %d features)', ver, len(feature_cols))
    # 모기지수 모델 + 메타 (선택)
    idx_model = None
    meta = None
    base_dir = os.path.dirname(mp)
    idx_path = os.path.join(base_dir, 'best_model_MosquitoIndex.joblib')
    meta_path = os.path.join(base_dir, 'training_meta.joblib')
    if os.path.exists(idx_path):
        try:
            idx_model = joblib.load(idx_path)
        except Exception as e:
            logger.warning('mosquito index model load failed: %s', e)
    if os.path.exists(meta_path):
        try:
            meta = joblib.load(meta_path)
        except Exception as e:
            logger.warning('training meta load failed: %s', e)
    return model, feature_cols, ver, idx_model, meta


def _build_v2_row(history, target_date, region_code, sido, weather):
    """v2 피처 row. history 는 target_date 직전까지의 [{date, count}, ...] (오름차순)."""
    counts = [h['count'] for h in history]
    n = len(counts)

    def lag(k):
        return counts[-k] if n >= k else (counts[0] if counts else 0)

    lag1 = lag(1); lag2 = lag(2); lag3 = lag(3); lag7 = lag(7)
    ma3 = sum(counts[-3:]) / min(3, n) if n > 0 else 0
    ma7 = sum(counts[-7:]) / min(7, n) if n > 0 else 0

    weekday = target_date.weekday()
    row = {
        'lag1': lag1, 'lag2': lag2, 'lag3': lag3, 'lag7': lag7,
        'ma3': ma3, 'ma7': ma7,
        'weekday': weekday, 'is_weekend': 1 if weekday >= 5 else 0,
        'month': target_date.month, 'day': target_date.day,
    }
    if weather:
        row['temperature'] = weather.get('temperature', 22.0) or 22.0
        row['humidity'] = weather.get('humidity', 60.0) or 60.0
        row['precipitation'] = weather.get('precipitation', 0.0) or 0.0
        row['wind_speed'] = weather.get('wind_speed', 2.0) or 2.0
    # one-hot 인코딩은 컬럼 정렬 시 채워짐
    row[f'region_code_{region_code or "NONE"}'] = 1
    row[f'sido_{sido or "NONE"}'] = 1
    return row


def _build_v1_row(history, target_date, weather, station_code):
    """v1 모델 호환용 row (기존 청주 모델). 백업용으로 유지."""
    _WEATHER_DEFAULT = {
        '평균기온': 27.0, '최고기온': 31.0, '최저기온': 23.5,
        '일강수량': 5.0, '평균풍속': 1.8, '평균습도': 78.0,
        '평균이슬점온도': 23.0, '평균지면온도': 28.5,
    }
    w = {**_WEATHER_DEFAULT, **(weather or {})}
    dt = pd.to_datetime(target_date)
    row = {
        '평균기온': w['평균기온'], '최고기온': w['최고기온'], '최저기온': w['최저기온'],
        '일강수량': w['일강수량'], '평균풍속': w['평균풍속'], '평균습도': w['평균습도'],
        '평균이슬점온도': w['평균이슬점온도'], '평균지면온도': w['평균지면온도'],
        '요일': dt.weekday(), '월': dt.month, '일': dt.day,
    }
    for col in ('평균기온', '일강수량', '평균습도'):
        for lag in (1, 2, 3, 5, 7):
            row[f'{col}_lag{lag}'] = w[col]
        for window in (3, 7):
            row[f'{col}_ma{window}'] = w[col]
    for window in (3, 7):
        row[f'누적강수량_{window}일'] = w['일강수량'] * window
    row['일교차'] = round(w['최고기온'] - w['최저기온'], 1)
    row['측정소_code'] = station_code
    return row


def predict_for_devices(devices_stats, weather_by_region=None, days_ahead=3):
    """장비별 예측 (recursive). devices_stats:
       [{uuid, name, region, history:[{date,count}], region_code?, sido?, weather?}]
    """
    model, feature_cols, ver, idx_model, meta = _load()
    days_ahead = max(1, min(int(days_ahead or 3), 14))
    # 모기지수 메타
    p95 = (meta or {}).get('p95', 300.0)

    # 영업일 기준 오늘 (새벽 5시가 일 경계)
    try:
        from moscom.timeutil import business_today
        today = business_today()
    except Exception:
        today = datetime.now(timezone(timedelta(hours=9))).date()
    future_dates = [today + timedelta(days=i) for i in range(0, days_ahead)]

    results = []
    for dev in devices_stats:
        nm = dev.get('name', '') or ''
        uid = dev.get('uuid', '')
        # 히스토리 복사 — recursive 로 예측값을 뒤에 붙여가며 다음 날 lag 로 사용
        hist = [{'date': h['date'], 'count': h['count']} for h in (dev.get('history') or [])]

        preds = []
        for td in future_dates:
            if ver == 'v2':
                row = _build_v2_row(
                    history=hist, target_date=td,
                    region_code=dev.get('region_code') or '',
                    sido=dev.get('sido') or '',
                    weather=dev.get('weather') or {},
                )
            else:
                station_code = 0
                station_map = {'가경천변': 0, '송절방죽': 1, '오송호수공원': 2}
                for key, code in station_map.items():
                    if key in nm:
                        station_code = code
                        break
                weather = (weather_by_region or {}).get(dev.get('region', ''))
                row = _build_v1_row(hist, td, weather, station_code)

            # DataFrame 1행 → feature_cols 맞춰 fill
            X = pd.DataFrame([row])
            for col in feature_cols:
                if col not in X.columns:
                    X[col] = 0
            X = X[feature_cols].astype('float64')
            yhat = float(np.maximum(model.predict(X)[0], 0))
            yhat_int = int(round(yhat))

            # 모기지수 예측: 학습된 모델이 있으면 그걸로, 없으면 마릿수에서 직접 산출
            idx_val = None
            if idx_model is not None:
                try:
                    idx_val = float(max(0.0, min(100.0, idx_model.predict(X)[0])))
                except Exception:
                    idx_val = None
            if idx_val is None:
                # fallback — predict 결과 마릿수 + 최근 7일 history + dev weather 로 직접 계산
                try:
                    from moscom.mosquito_index import compute_index as _ci
                    recent7 = [h['count'] for h in hist[-7:]]
                    w = dev.get('weather') or {}
                    mi = _ci(
                        count=yhat_int, last7_counts=recent7,
                        temperature=w.get('temperature'), humidity=w.get('humidity'),
                        p95=p95, name=nm, addr=dev.get('region', ''), detail='',
                    )
                    idx_val = mi['index']
                except Exception:
                    idx_val = None

            # 4단계 등급 (모기지수 기준)
            def _grade_idx(v):
                if v is None: return None
                if v < 25: return '쾌적'
                if v < 50: return '관심'
                if v < 75: return '주의'
                return '불쾌'

            preds.append({
                'date': td.isoformat(),
                'predicted': yhat_int,
                'predicted_index': round(idx_val, 1) if idx_val is not None else None,
                'grade': _grade_idx(idx_val),
            })
            # 다음 lag 를 위해 hist 에 예측값 push
            hist.append({'date': td.isoformat(), 'count': yhat_int})

        results.append({
            'uuid': uid,
            'name': nm,
            'region': dev.get('region', ''),
            'predictions': preds,
            'history': dev.get('history') or [],  # 원본 history (예측값 안 들어간 거)
        })

    # 등급 + 근거
    def grade(n):
        if n <= 10: return '안전'
        if n <= 50: return '관심'
        if n <= 100: return '주의'
        if n <= 200: return '경고'
        return '위험'

    for r in results:
        ps = [p['predicted'] for p in r['predictions']]
        r['max_predicted'] = max(ps) if ps else 0
        r['avg_predicted'] = round(sum(ps) / len(ps)) if ps else 0
        # 모기지수 집계
        idx_list = [p.get('predicted_index') for p in r['predictions'] if p.get('predicted_index') is not None]
        if idx_list:
            max_idx = max(idx_list)
            avg_idx = sum(idx_list) / len(idx_list)
            r['max_index'] = round(max_idx, 1)
            r['avg_index'] = round(avg_idx, 1)
            # 등급 = 평균 모기지수의 4단계 등급
            if avg_idx < 25:   r['grade'] = '쾌적'
            elif avg_idx < 50: r['grade'] = '관심'
            elif avg_idx < 75: r['grade'] = '주의'
            else:              r['grade'] = '불쾌'
        else:
            # 모기지수 없으면 fallback — 기존 마릿수 기반 5단계
            r['max_index'] = None
            r['avg_index'] = None
            r['grade'] = grade(r['max_predicted'])
        # 추론 근거
        hist = r.get('history') or []
        parts = []
        if hist:
            recent = [h['count'] for h in hist[-7:]]
            last = recent[-1] if recent else 0
            avg7 = sum(recent) / len(recent) if recent else 0
            if avg7 > 0:
                dp = round((last - avg7) / avg7 * 100)
                if dp > 15: parts.append(f'최근 7일 평균 대비 +{dp}% 상승')
                elif dp < -15: parts.append(f'최근 7일 평균 대비 {dp}% 하락')
                else: parts.append('최근 7일 추세 안정')
            else:
                parts.append(f'최근 평균 {avg7:.1f}마리 / 직전 {last}마리')
        if ps and len(ps) >= 2:
            if ps[-1] > ps[0] * 1.1: parts.append('향후 증가 예상')
            elif ps[-1] < ps[0] * 0.9: parts.append('향후 감소 예상')
            else: parts.append('향후 유지 예상')
        # 기상 근거 (기온·습도)
        wx = dev.get('weather') or {}
        wt = wx.get('temperature')
        wh = wx.get('humidity')
        if wt is not None:
            if 25 <= wt <= 28: parts.append(f'기온 {wt}°C 우화 최적')
            elif 20 <= wt < 25: parts.append(f'기온 {wt}°C 발생 적정')
            elif wt > 28: parts.append(f'기온 {wt}°C 활동 다소 둔화')
            else: parts.append(f'기온 {wt}°C 발생 억제')
        if wh is not None and wh >= 70:
            parts.append(f'습도 {wh}% 생존 유리')
        if ver == 'v2':
            parts.append(f'모델 v2 · 자체 데이터 학습')
        r['reasoning'] = ' · '.join(parts) if parts else '데이터 부족'

        # 신뢰도
        hist_days = len(hist)
        base = 60
        if hist_days >= 14: base += 20
        elif hist_days >= 7: base += 12
        elif hist_days >= 3: base += 5
        r['confidence'] = min(base, 92)

    return results


def backcast_for_date(history, target_date, region_code='', sido='', weather=None):
    """과거 예측(backcast) — target_date 를 방역 미적용으로 예측했다면 얼마였을지.
    history: 전체 [{date, count}] (오름차순 가정). target_date 이전 데이터만 lag 로 사용.
    반환: 예측 마릿수(int) 또는 None(모델/데이터 부족).
    방역 효과 검증에서 '예상' 값으로 사용."""
    try:
        model, feature_cols, ver, idx_model, meta = _load()
        if model is None or ver != 'v2':
            return None  # v2 모델일 때만 지원(피처 일관성)
        if isinstance(target_date, str):
            td = datetime.strptime(target_date[:10], '%Y-%m-%d').date()
        else:
            td = target_date
        # target_date 직전까지의 history 만 사용 (누출 방지)
        prior = [h for h in (history or []) if (h.get('date') or '')[:10] < td.isoformat()]
        prior.sort(key=lambda h: h['date'])
        if len(prior) < 3:
            return None  # lag 계산에 필요한 최소 데이터 부족
        row = _build_v2_row(history=prior, target_date=td,
                            region_code=region_code or '', sido=sido or '',
                            weather=weather or {})
        X = pd.DataFrame([row])
        for col in feature_cols:
            if col not in X.columns:
                X[col] = 0
        X = X[feature_cols].astype('float64')
        yhat = float(np.maximum(model.predict(X)[0], 0))
        return int(round(yhat))
    except Exception:
        logger.exception('backcast_for_date failed')
        return None
