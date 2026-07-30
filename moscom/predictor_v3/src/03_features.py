"""3단계: 피처 생성.

규약 (누수 방지)
  기준일 d 에서 d+h 의 포집량을 예측한다. 입력으로 쓸 수 있는 것은
    - 포집량: d, d-1, ..., d-6  (과거 7일)
    - 기상  : d, d-1, ..., d-6  (실측). d+h 기상은 실제 운영에선 예보라
              '알고 있는 값'이 아니므로 사용하지 않는다.
    - 달력  : d+h 의 요일/월/연중일 (미래여도 확정값이므로 사용 가능)
    - 관측소: sid/region (정적)
  y 는 log1p 변환 후 학습하고, 평가 시 expm1 로 되돌린다.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import PANEL_CSV, WEATHER_CSV, FEATURES_CSV, LAG_WINDOW, HORIZONS

WEATHER_BASE = ["temperature_2m_mean", "temperature_2m_max", "temperature_2m_min",
                "precipitation_sum", "night_temp", "night_temp_min",
                "night_humid", "night_precip", "night_wind"]


def add_target_lags(g: pd.DataFrame) -> pd.DataFrame:
    """관측소 1개에 대한 과거 7일 기반 피처."""
    y = g["y"]
    ylog = np.log1p(y)

    for k in range(1, LAG_WINDOW + 1):
        g[f"lag{k}"] = ylog.shift(k)

    # 롤링 통계 — shift(1) 후 계산해 당일 값이 새지 않도록
    prev = ylog.shift(1)
    for w in (3, 7):
        g[f"roll{w}_mean"] = prev.rolling(w, min_periods=max(2, w // 2)).mean()
        g[f"roll{w}_std"] = prev.rolling(w, min_periods=max(2, w // 2)).std()
        g[f"roll{w}_max"] = prev.rolling(w, min_periods=max(2, w // 2)).max()

    # 추세: 최근 3일 평균 - 직전 4~7일 평균
    g["trend_3v7"] = g["roll3_mean"] - g["roll7_mean"]
    g["diff1"] = g["lag1"] - g["lag2"]
    g["diff2"] = g["lag2"] - g["lag3"]

    # 최근 7일 중 실제 관측된 날 비율 (결측 많은 구간 신뢰도 지표)
    g["obs_ratio7"] = y.notna().shift(1).rolling(7, min_periods=1).mean()
    # 최근 7일 0마리 비율 (계절 초반 무발생 구간 신호)
    g["zero_ratio7"] = (y == 0).shift(1).rolling(7, min_periods=2).mean()

    # 관측소 누적 경험치 — 시즌 내 위치
    g["days_since_start"] = np.arange(len(g))

    # --- RAW 원본에서만 얻을 수 있는 장비 상태 피처 ---
    # 팬 가동시간 = 실제 포집 시도량. 0시간이면 '모기 없음'이 아니라 '장비 미작동'.
    if "fan_hours" in g:
        g["fan_hours_d0"] = g["fan_hours"]
        g["fan_hours_lag1"] = g["fan_hours"].shift(1)
        g["fan_hours_m3"] = g["fan_hours"].shift(1).rolling(3, min_periods=2).mean()
        # 포집량을 가동시간으로 정규화 -> 가동률 차이를 보정한 '시간당 포집강도'
        g["rate_per_fanhour"] = np.log1p(y / g["fan_hours"].replace(0, np.nan))
        g["rate_lag1"] = g["rate_per_fanhour"].shift(1)
        g["rate_m3"] = g["rate_per_fanhour"].shift(1).rolling(3, min_periods=2).mean()
    if "n_meas" in g:
        g["n_meas_d0"] = g["n_meas"]
        g["meas_ratio7"] = g["n_meas"].shift(1).rolling(7, min_periods=2).mean() / 12
    if "battery" in g:
        g["battery_d0"] = g["battery"]
        g["battery_m3"] = g["battery"].shift(1).rolling(3, min_periods=2).mean()
    if "device_off" in g:
        g["off_ratio7"] = g["device_off"].shift(1).rolling(7, min_periods=2).mean()
    if "peak_hour" in g:
        # 피크 시각은 개체 활동 리듬의 대리지표 (미포집일 -1)
        g["peak_hour_d0"] = g["peak_hour"]
        g["peak_hour_lag1"] = g["peak_hour"].shift(1)
    return g


def add_weather_lags(g: pd.DataFrame) -> pd.DataFrame:
    """권역 1개에 대한 기상 lag/누적 피처 (기준일 d 까지만 사용)."""
    for col in WEATHER_BASE:
        if col not in g:
            continue
        g[f"w_{col}_d0"] = g[col]                       # 기준일 당일 실측
        g[f"w_{col}_lag1"] = g[col].shift(1)
        g[f"w_{col}_m3"] = g[col].rolling(3, min_periods=2).mean()
        g[f"w_{col}_m7"] = g[col].rolling(7, min_periods=4).mean()

    # 모기 개체 발생은 유충 기간(약 1~2주) 누적 온도·강수에 좌우
    if "temperature_2m_mean" in g:
        t = g["temperature_2m_mean"]
        # 발육영점온도 10°C 기준 누적 유효적산온도(GDD)
        gdd = (t - 10).clip(lower=0)
        g["w_gdd_7"] = gdd.rolling(7, min_periods=4).sum()
        g["w_gdd_14"] = gdd.rolling(14, min_periods=7).sum()
    if "precipitation_sum" in g:
        p = g["precipitation_sum"]
        g["w_precip_7"] = p.rolling(7, min_periods=4).sum()
        g["w_precip_14"] = p.rolling(14, min_periods=7).sum()
        # 산란처 형성: 강수 후 며칠 뒤 개체 증가 -> 3~10일 전 누적 강수
        g["w_precip_lag3_10"] = p.shift(3).rolling(8, min_periods=4).sum()
        g["w_days_since_rain"] = (
            p.gt(1.0).astype(int).groupby(p.gt(1.0).cumsum()).cumcount()
        )
    return g


def add_cross_section(df: pd.DataFrame) -> pd.DataFrame:
    """관측소 자기정규화 + 권역/전국 동시성 피처.

    실험 결과 가장 기여가 큰 블록. 특히 권역 동시성(같은 날 같은 권역의 다른
    관측소 수준)은 h=3 로그 R2 를 0.34 -> 0.42 로 끌어올렸다. 기상 대리변수보다
    강한 실측 신호이기 때문.
    """
    df = df.sort_values(["sid", "bizdate"]).copy()
    ylog = np.log1p(df["y"])
    df["_yl"] = ylog
    grp = ylog.groupby(df["sid"])

    # 1) 자기 수준 대비 상대 위치 — 관측소 간 규모 차이를 제거한 신호
    m14 = grp.transform(lambda s: s.shift(1).rolling(14, min_periods=4).mean())
    s14 = grp.transform(lambda s: s.shift(1).rolling(14, min_periods=4).std())
    df["z_vs_own14"] = (ylog - m14) / s14.replace(0, np.nan)
    df["ratio_vs_own14"] = ylog - m14          # 로그차 = 평소 대비 배율
    df["own_vol14"] = s14
    df["own_vol7"] = grp.transform(lambda s: s.shift(1).rolling(7, min_periods=3).std())

    # 2) 권역 동시성 — 자기 자신을 제외한(LOO) 권역 평균
    #    자기참조 누수를 막기 위해 합계에서 본인 값을 뺀 뒤 평균낸다.
    g = df.groupby(["region", "bizdate"])["_yl"]
    ssum, scnt = g.transform("sum"), g.transform("count")
    df["region_daymean"] = (ssum - df["_yl"]) / (scnt - 1).replace(0, np.nan)
    df["region_dev"] = ylog - df["region_daymean"]

    rd = (df.groupby(["region", "bizdate"])["_yl"].mean().rename("rm")
          .reset_index().sort_values(["region", "bizdate"]))
    rd["region_diff1"] = rd.groupby("region")["rm"].diff()
    rd["region_diff3"] = rd.groupby("region")["rm"].diff(3)
    df = df.merge(rd[["region", "bizdate", "region_diff1", "region_diff3"]],
                  on=["region", "bizdate"], how="left")

    # 3) 전국 동시성 — 전 관측소 공통 급증/급감
    nd = df.groupby("bizdate")["_yl"].mean().rename("nm").reset_index()
    nd["net_diff1"] = nd["nm"].diff()
    nd["net_diff3"] = nd["nm"].diff(3)
    df = df.merge(nd[["bizdate", "net_diff1", "net_diff3"]], on="bizdate", how="left")
    return df.drop(columns="_yl")


def build() -> pd.DataFrame:
    panel = pd.read_csv(PANEL_CSV, parse_dates=["bizdate"])
    weather = pd.read_csv(WEATHER_CSV, parse_dates=["date"])

    weather = weather.sort_values(["region", "date"])
    weather = pd.concat(
        [add_weather_lags(g.copy()) for _, g in weather.groupby("region", sort=False)],
        ignore_index=True)
    wcols = [c for c in weather.columns if c.startswith("w_")]
    weather = weather[["region", "date"] + wcols]

    panel = panel.sort_values(["sid", "bizdate"])
    panel = pd.concat(
        [add_target_lags(g.copy()) for _, g in panel.groupby("sid", sort=False)],
        ignore_index=True)

    df = panel.merge(weather, left_on=["region", "bizdate"],
                     right_on=["region", "date"], how="left").drop(columns="date")
    df = add_cross_section(df)

    # --- 타깃: h일 뒤 실제 포집량 ---
    for h in HORIZONS:
        df[f"target_h{h}"] = df.groupby("sid")["y"].shift(-h)
        # 벤치마크: 기준일 값을 그대로 미래로 미는 persistence
        df[f"persist_h{h}"] = df["y"]

    # 달력 피처는 예측 대상일(d+h) 기준
    for h in HORIZONS:
        tdate = df["bizdate"] + pd.Timedelta(days=h)
        df[f"dow_h{h}"] = tdate.dt.dayofweek
        df[f"month_h{h}"] = tdate.dt.month
        df[f"doy_h{h}"] = tdate.dt.dayofyear
        df[f"is_weekend_h{h}"] = (tdate.dt.dayofweek >= 5).astype(int)

    # 관측소/권역 코드
    df["sid_code"] = df["sid"].astype("category").cat.codes
    df["region_code"] = df["region"].astype("category").cat.codes

    # 관측소 규모 수준 — 학습 구간 정보만 쓰도록 확장평균(누수 방지)
    ylog = np.log1p(df["y"])
    df["sid_expmean"] = (ylog.groupby(df["sid"]).apply(
        lambda s: s.shift(1).expanding(min_periods=3).mean()).reset_index(level=0, drop=True))

    print(f"[피처] 행수 {len(df):,}  컬럼 {df.shape[1]}")
    for h in HORIZONS:
        n = df[f"target_h{h}"].notna().sum()
        print(f"  h={h}: 타깃 존재 {n:,}행")
    return df


if __name__ == "__main__":
    out = build()
    out.to_csv(FEATURES_CSV, index=False, encoding="utf-8-sig")
    print(f"[저장] {FEATURES_CSV}")
