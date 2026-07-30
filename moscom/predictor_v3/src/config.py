"""version_3 공통 설정 (RAW 원본 기반)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "모기포집_RAW원본_20260729.xlsx"
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"
OUT_DIR = ROOT / "output"
for _d in (DATA_DIR, MODEL_DIR, OUT_DIR):
    _d.mkdir(exist_ok=True)

PANEL_CSV = DATA_DIR / "panel_daily.csv"
WEATHER_CSV = DATA_DIR / "weather_daily.csv"
FEATURES_CSV = DATA_DIR / "features.csv"

# --- 모델링 규약 ---
LAG_WINDOW = 7           # 과거 7일 입력
HORIZONS = [1, 2, 3]     # 1~3일 앞 예측
MIN_DAYS_EVAL = 60       # 평가 대상 최소 유효 관측일
VALID_DAYS = 21          # 홀드아웃 구간
SEED = 42

# 야간 수집창: 18시 ~ 익일 05시, 업무일 경계 새벽 5시
NIGHT_START, NIGHT_END = 18, 5

REGION_COORDS = {
    "서울특별시 강서구":       (37.5509, 126.8495),
    "서울특별시 양천구":       (37.5170, 126.8664),
    "서울특별시 동대문구":     (37.5744, 127.0396),
    "경기도 성남시 분당구":    (37.3828, 127.1189),
    "충청남도 천안시서북구":   (36.8151, 127.1139),
    "충청남도 천안시동남구":   (36.7998, 127.1523),
    "전라북도 군산시":         (35.9676, 126.7369),
    "전라남도 여수시":         (34.7604, 127.6622),
    "경상남도 김해시":         (35.2285, 128.8894),
    "경상남도 함안군":         (35.2725, 128.4064),
    "경상남도 함양군":         (35.5205, 127.7253),
    "경상남도 창원시 마산합포구": (35.1997, 128.5649),
    "부산광역시 중구":         (35.1064, 129.0323),
}
