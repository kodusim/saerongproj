"""
AI 모기 발생 예측기
- RandomForest 모델 (core/ml/best_model_RandomForest.joblib) 사용
- MOSCOM 일별 포집 데이터에서 lag/ma 피처 생성
- 기상 피처는 "최근 7일 평균" 대체값으로 채움 (장비가 있는 지역의 관측치가 별도로 없으므로)
- 학습 데이터가 청주 3개소·여름 2개월이라, 전국·임의 시기에 쓰면 '참고값' 수준임
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_MODEL_DIR = os.path.join(os.path.dirname(__file__), 'ml')
_MODEL_PATH = os.path.join(_MODEL_DIR, 'best_model_RandomForest.joblib')
_FEATURES_PATH = os.path.join(_MODEL_DIR, 'feature_cols.joblib')

# 학습 데이터에서 관측된 기상 대략값 (summer 청주). 기상 미제공 시 디폴트.
_WEATHER_DEFAULT = {
    '평균기온': 27.0,
    '최고기온': 31.0,
    '최저기온': 23.5,
    '일강수량': 5.0,
    '평균풍속': 1.8,
    '평균습도': 78.0,
    '평균이슬점온도': 23.0,
    '평균지면온도': 28.5,
}


@lru_cache(maxsize=1)
def _load():
    """모델과 피처 리스트 lazy load (메모리 절약)"""
    import joblib
    if not os.path.exists(_MODEL_PATH):
        raise FileNotFoundError(f'model not found: {_MODEL_PATH}')
    model = joblib.load(_MODEL_PATH)
    feature_cols = joblib.load(_FEATURES_PATH)
    logger.info('AI model loaded (%d features)', len(feature_cols))
    return model, feature_cols


def _build_feature_row(history, target_date, weather, station_code):
    """단일 장비·단일 날짜의 feature row 생성
    history: [{date: 'YYYY-MM-DD', count: int}, ...] (target_date 이전 일별 실측, 오름차순)
    weather: 기상 피처 dict (None이면 기본값)
    station_code: 0=가경천변/1=송절방죽/2=오송호수공원 (학습 때 3곳만) → 그 외는 0
    """
    w = {**_WEATHER_DEFAULT, **(weather or {})}

    # 날짜 변수
    dt = pd.to_datetime(target_date)
    row = {
        '평균기온': w['평균기온'], '최고기온': w['최고기온'], '최저기온': w['최저기온'],
        '일강수량': w['일강수량'], '평균풍속': w['평균풍속'], '평균습도': w['평균습도'],
        '평균이슬점온도': w['평균이슬점온도'], '평균지면온도': w['평균지면온도'],
        '요일': dt.weekday(), '월': dt.month, '일': dt.day,
    }

    # history → pandas Series (date indexed)
    if history:
        hist = pd.DataFrame(history)
        hist['date'] = pd.to_datetime(hist['date'])
        hist = hist.sort_values('date').set_index('date')['count']
    else:
        hist = pd.Series(dtype='float64')

    def lag_of(col, lag):
        # 학습 때 모기 count가 아닌 기상 lag였지만 MOSCOM엔 기상 이력이 없으니
        # 모든 기상 lag는 현재 기상값으로 대체 (분포 흐트러뜨리지 않게)
        if col in ('평균기온', '일강수량', '평균습도'):
            return w[col]
        return w.get(col, 0.0)

    for col in ('평균기온', '일강수량', '평균습도'):
        for lag in (1, 2, 3, 5, 7):
            row[f'{col}_lag{lag}'] = lag_of(col, lag)
        for window in (3, 7):
            row[f'{col}_ma{window}'] = w[col]
    for window in (3, 7):
        row[f'누적강수량_{window}일'] = w['일강수량'] * window
    row['일교차'] = round(w['최고기온'] - w['최저기온'], 1)
    row['측정소_code'] = station_code

    return row


def predict_for_devices(devices_stats, weather_by_region=None, days_ahead=3):
    """장비별 예측
    devices_stats: [
      {
        'uuid': str,
        'name': str,
        'region': str,             # 'sido gungu'
        'history': [{date, count}, ...]  # 최근 7일 이상
      }, ...
    ]
    weather_by_region: {region_key: {평균기온, 평균습도, ...}} — 기상 dict 덮어쓰기용 (옵셔널)
    days_ahead: 예측할 미래 일수 (기본 3, 최대 14)

    반환: [{uuid, name, region, predictions: [{date, predicted}, ...], grade, ...}]
    """
    model, feature_cols = _load()

    days_ahead = max(1, min(int(days_ahead or 3), 14))

    # 내일~+days_ahead일 후 예측
    today = datetime.now(timezone(timedelta(hours=9))).date()
    future_dates = [today + timedelta(days=i) for i in range(1, days_ahead + 1)]

    results = []
    rows_to_predict = []
    index_map = []  # (result_idx, date_idx)

    # 측정소 코드 매핑
    station_map = {'가경천변': 0, '송절방죽': 1, '오송호수공원': 2}

    for i, dev in enumerate(devices_stats):
        nm = dev.get('name', '') or ''
        station_code = 0
        for key, code in station_map.items():
            if key in nm:
                station_code = code
                break
        weather = (weather_by_region or {}).get(dev.get('region', ''))

        dev_rows = []
        for j, td in enumerate(future_dates):
            row = _build_feature_row(dev.get('history') or [], td, weather, station_code)
            dev_rows.append(row)
            index_map.append((i, j))
            rows_to_predict.append(row)

        results.append({
            'uuid': dev.get('uuid', ''),
            'name': nm,
            'region': dev.get('region', ''),
            'predictions': [{'date': td.isoformat(), 'predicted': None} for td in future_dates],
        })

    if not rows_to_predict:
        return []

    # 누락된 feature는 0으로 채움
    X = pd.DataFrame(rows_to_predict)
    for col in feature_cols:
        if col not in X.columns:
            X[col] = 0
    X = X[feature_cols]
    preds = np.maximum(model.predict(X), 0).round().astype(int)

    for k, p in enumerate(preds):
        i, j = index_map[k]
        results[i]['predictions'][j]['predicted'] = int(p)

    # 등급 산출 (최대 예측값 기준)
    def grade(n):
        if n <= 10: return '안전'
        if n <= 50: return '관심'
        if n <= 100: return '주의'
        if n <= 200: return '경고'
        return '위험'

    for i, r in enumerate(results):
        ps = [p['predicted'] for p in r['predictions']]
        r['max_predicted'] = max(ps) if ps else 0
        r['avg_predicted'] = round(sum(ps) / len(ps)) if ps else 0
        r['grade'] = grade(r['max_predicted'])

        # 최근 7일 실측값 복원 (프론트 차트용)
        hist = devices_stats[i].get('history') or []
        r['history'] = hist

        # 추론 근거 텍스트 생성
        reasoning_parts = []
        if hist:
            recent = [h['count'] for h in hist[-7:]]
            avg7 = sum(recent) / len(recent) if recent else 0
            last = recent[-1] if recent else 0
            if avg7 > 0:
                delta_pct = round((last - avg7) / avg7 * 100)
                if delta_pct > 15:
                    reasoning_parts.append(f'최근 7일 평균 대비 +{delta_pct}% 상승')
                elif delta_pct < -15:
                    reasoning_parts.append(f'최근 7일 평균 대비 {delta_pct}% 하락')
                else:
                    reasoning_parts.append('최근 7일 추세 안정')
            # 트렌드 (앞 절반 vs 뒤 절반)
            half = len(recent) // 2
            if half >= 2:
                first_half = sum(recent[:half]) / half
                second_half = sum(recent[half:]) / (len(recent) - half)
                if first_half > 0:
                    tr = round((second_half - first_half) / first_half * 100)
                    if tr > 20:
                        reasoning_parts.append('후반 급증 패턴')
                    elif tr < -20:
                        reasoning_parts.append('후반 감소 패턴')
        # 예측 변화
        if ps and len(ps) >= 2:
            if ps[-1] > ps[0] * 1.1:
                reasoning_parts.append('향후 3일 증가 예상')
            elif ps[-1] < ps[0] * 0.9:
                reasoning_parts.append('향후 3일 감소 예상')
            else:
                reasoning_parts.append('향후 3일 유지 예상')
        # 기상 조건
        reasoning_parts.append('기온·습도 적정 조건 가정')
        r['reasoning'] = ' · '.join(reasoning_parts) if reasoning_parts else '데이터 부족'

        # 가중 신뢰도 (history 많을수록 / 측정소 매칭 시 높게)
        hist_days = len(hist)
        nm = devices_stats[i].get('name', '')
        matched_station = any(k in nm for k in ('가경천변', '송절방죽', '오송호수공원'))
        base = 60
        if hist_days >= 7: base += 15
        elif hist_days >= 3: base += 8
        if matched_station: base += 12
        r['confidence'] = min(base, 95)

    return results
