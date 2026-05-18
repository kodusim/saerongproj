"""모기지수 산출 (우리만의 정의)

공식 (0~100 스케일):

  지수 = 0.5 × 마릿수정규화 + 0.2 × 7일추세 + 0.2 × 기상조건 + 0.1 × 권역가중치

각 구성요소:
  1. 마릿수정규화 (50%) — 우리 데이터 95퍼센타일 기준 비선형
       M = min(100, sqrt(today_count / P95) × 100)
       P95 = 학습시 전체 일별 분포 95분위 (자동 산출, 모델과 함께 저장)

  2. 7일 추세 (20%) — 최근 7일 평균 대비 변화율
       T = 50 + clip((today / avg7 − 1) × 50, −50, +50)
       avg7 = today, T = 50 / 2배 → 100 / 0 → 0

  3. 기상조건 (20%) — 모기 활동 적정도
       기온점수 = max(0, 100 − abs(temp − 25) × 100/15)   # 25°C 최적, ±15°C 에서 0
       습도점수 = clip(humidity, 0, 100)                    # 그대로 사용 (%)
       W = 0.6 × 기온점수 + 0.4 × 습도점수

  4. 권역가중치 (10%) — 장비 위치 특성
       기본 60
       + 수변부 30 / 공원 15 / 주거지 10 / 농촌 5 / 산림 0
       cap 100

등급 (4단계):
  0~25  쾌적
  25~50 관심
  50~75 주의
  75~100 불쾌
"""
import math
from typing import Optional, Iterable


# ─ 권역(habitat) 가중치 ─────────────────────────
HABITAT_BONUS = {
    '수변부': 30, '수변': 30, '하천': 30, '연못': 30, '저수지': 30,
    '공원': 15, '체육공원': 15,
    '주거지': 10, '아파트': 10, '단지': 10,
    '농촌': 5, '농지': 5, '농장': 5,
    '산림': 0, '숲': 0,
}


def habitat_weight(name: str = '', addr: str = '', detail: str = '') -> int:
    """장비 이름/주소 키워드로 권역 가중치 추정."""
    text = f'{name} {addr} {detail}'
    bonus = 0
    for key, b in HABITAT_BONUS.items():
        if key in text:
            bonus = max(bonus, b)
    return min(100, 60 + bonus)


# ─ 각 축 계산 ───────────────────────────────────

def axis_count(count: float, p95: float) -> float:
    """1축. 마릿수 정규화 (0~100). P95 기준 sqrt 변환."""
    if p95 <= 0:
        p95 = 100.0
    c = max(0.0, float(count))
    score = math.sqrt(c / p95) * 100
    return float(min(100.0, score))


def axis_trend(today_count: float, last7_counts: Iterable[float]) -> float:
    """2축. 7일 추세 (0~100). 최근 7일 평균 대비."""
    vals = [v for v in (last7_counts or []) if v is not None]
    if not vals:
        return 50.0
    avg7 = sum(vals) / len(vals)
    if avg7 <= 0:
        # 7일 평균이 0 → 오늘 0이면 50, 양수면 100
        return 50.0 if today_count <= 0 else 100.0
    delta = (today_count / avg7 - 1.0)  # -1 ~ +∞
    score = 50.0 + max(-50.0, min(50.0, delta * 50.0))
    return float(max(0.0, min(100.0, score)))


def axis_weather(temperature: Optional[float], humidity: Optional[float]) -> float:
    """3축. 기상 조건 (0~100). 25°C 최적 + 습도 그대로."""
    t = 22.0 if temperature is None else float(temperature)
    h = 60.0 if humidity is None else float(humidity)
    temp_score = max(0.0, 100.0 - abs(t - 25.0) * (100.0 / 15.0))
    humid_score = max(0.0, min(100.0, h))
    w = 0.6 * temp_score + 0.4 * humid_score
    return float(max(0.0, min(100.0, w)))


def axis_habitat(name: str = '', addr: str = '', detail: str = '') -> float:
    """4축. 권역 가중치 (0~100)."""
    return float(habitat_weight(name, addr, detail))


# ─ 종합 ─────────────────────────────────────────

WEIGHTS = (0.5, 0.2, 0.2, 0.1)  # 마릿수, 추세, 기상, 권역


def compute_index(count: float, last7_counts: Iterable[float],
                  temperature: Optional[float], humidity: Optional[float],
                  p95: float = 300.0,
                  name: str = '', addr: str = '', detail: str = '') -> dict:
    """모기지수 종합 계산.
    Returns: {index, grade, parts: {count_norm, trend, weather, habitat}}
    """
    m = axis_count(count, p95)
    t = axis_trend(count, last7_counts)
    w = axis_weather(temperature, humidity)
    h = axis_habitat(name, addr, detail)
    wm, wt, ww, wh = WEIGHTS
    idx = wm * m + wt * t + ww * w + wh * h
    return {
        'index': round(idx, 1),
        'grade': grade_of(idx),
        'parts': {
            'count_norm': round(m, 1),
            'trend': round(t, 1),
            'weather': round(w, 1),
            'habitat': round(h, 1),
        },
        'weights': {'count': wm, 'trend': wt, 'weather': ww, 'habitat': wh},
        'p95': p95,
    }


def grade_of(index: float) -> str:
    """4단계 등급."""
    if index < 25:
        return '쾌적'
    if index < 50:
        return '관심'
    if index < 75:
        return '주의'
    return '불쾌'


# 사람이 읽기 좋은 수식 표기 (UI 표시용)
FORMULA_TEXT = (
    '모기지수 = 0.5×마릿수정규화 + 0.2×7일추세 + 0.2×기상조건 + 0.1×권역가중치\n'
    '  · 마릿수정규화 = min(100, √(오늘마릿수 / P95) × 100)\n'
    '  · 7일추세 = 50 + clip((오늘/7일평균 − 1) × 50, ±50)\n'
    '  · 기상조건 = 0.6 × max(0, 100 − |기온−25| × 100/15) + 0.4 × 습도(%)\n'
    '  · 권역가중치 = 60 + (수변부 30 / 공원 15 / 주거지 10 / 농촌 5 / 산림 0)'
)
