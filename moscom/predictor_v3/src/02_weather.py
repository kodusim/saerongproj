"""2단계: 권역별 일별 기상 수집 (Open-Meteo, API 키 불필요).

기상청 ASOS API는 공공데이터포털 서비스키가 필요해 이 환경에서는 사용 불가.
Open-Meteo ERA5 재분석 아카이브는 키 없이 동일 기간·전 지역을 커버하므로 이를 사용.

주의: 모기 포집은 야간(18~05시) 수집창 기준이므로, 일평균뿐 아니라
      야간 시간대(18~05시) 평균 기온·습도·강수를 별도로 계산해 붙인다.
"""
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import PANEL_CSV, WEATHER_CSV, REGION_COORDS

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"
HOURLY = ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"]
DAILY = ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
         "precipitation_sum", "wind_speed_10m_max"]


def _get(url: str, params: dict) -> dict:
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
            print(f"    HTTP {r.status_code}: {r.text[:200]}")
        except Exception as exc:  # 네트워크 일시 오류 재시도
            print(f"    요청 실패({attempt + 1}/4): {exc}")
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"기상 API 호출 실패: {url}")


def fetch_region(name: str, lat: float, lon: float,
                 start: str, end: str) -> pd.DataFrame:
    """한 권역의 일별 + 야간창 기상을 반환."""
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "hourly": ",".join(HOURLY), "daily": ",".join(DAILY),
        "timezone": "Asia/Seoul",
    }
    js = _get(ARCHIVE, params)
    if "daily" not in js or not js["daily"].get("time"):
        raise RuntimeError(f"{name}: 아카이브 응답에 daily 없음")

    daily = pd.DataFrame(js["daily"]).rename(columns={"time": "date"})
    daily["date"] = pd.to_datetime(daily["date"])

    # --- 야간 수집창(18시~익일 05시)을 '업무일'에 귀속시켜 집계 ---
    h = pd.DataFrame(js["hourly"]).rename(columns={"time": "dt"})
    h["dt"] = pd.to_datetime(h["dt"])
    hh = h["dt"].dt.hour
    night = h[(hh >= 18) | (hh <= 5)].copy()
    # 00~05시는 전날 업무일 소속
    night["bizdate"] = night["dt"].dt.normalize().where(
        night["dt"].dt.hour >= 18,
        night["dt"].dt.normalize() - pd.Timedelta(days=1),
    )
    night_agg = night.groupby("bizdate").agg(
        night_temp=("temperature_2m", "mean"),
        night_temp_min=("temperature_2m", "min"),
        night_humid=("relative_humidity_2m", "mean"),
        night_precip=("precipitation", "sum"),
        night_wind=("wind_speed_10m", "mean"),
        night_hours=("temperature_2m", "size"),
    ).reset_index()
    # 12시간이 온전히 없는 경계일은 제외
    night_agg = night_agg[night_agg["night_hours"] == 12].drop(columns="night_hours")

    out = daily.merge(night_agg, left_on="date", right_on="bizdate", how="left")
    out = out.drop(columns=["bizdate"])
    out.insert(0, "region", name)
    return out


def main() -> None:
    panel = pd.read_csv(PANEL_CSV, parse_dates=["bizdate"])
    regions = sorted(panel["region"].unique())
    start = panel["bizdate"].min().strftime("%Y-%m-%d")
    end = panel["bizdate"].max().strftime("%Y-%m-%d")

    missing = [r for r in regions if r not in REGION_COORDS]
    if missing:
        raise SystemExit(f"좌표 미등록 권역: {missing} -> config.REGION_COORDS 에 추가 필요")

    print(f"[기상] Open-Meteo ERA5 아카이브 · {start} ~ {end} · {len(regions)}개 권역")
    frames = []
    for i, name in enumerate(regions, 1):
        lat, lon = REGION_COORDS[name]
        df = fetch_region(name, lat, lon, start, end)
        frames.append(df)
        print(f"  [{i:2d}/{len(regions)}] {name:<22} {len(df):3d}일  "
              f"평균기온 {df['temperature_2m_mean'].mean():5.1f}°C  "
              f"야간결측 {int(df['night_temp'].isna().sum())}일")
        time.sleep(0.4)  # 공개 API 예의상 간격

    w = pd.concat(frames, ignore_index=True)
    w.to_csv(WEATHER_CSV, index=False, encoding="utf-8-sig")
    print(f"[저장] {WEATHER_CSV}  ({len(w):,}행)")


if __name__ == "__main__":
    main()
