"""1단계: RAW 측정 로그 -> 관측소×업무일 패널.

version_2(가공본) 대비 이 단계에서 새로 얻는 것
  - 장비 단위 식별자(device)로 동명 관측소를 정확히 분리
  - 리셋 플래그 + 미플래그 롤백을 함께 방어 (원본엔 미플래그 롤백 2,913건 존재)
  - 팬 가동/배터리 상태를 일별로 집계해 '장비 미작동'과 '실제 0'을 구분

처리 규칙
  1. (device, ts) 중복은 누적값 최대치만 남김 (같은 시각 중복 전송)
  2. 누적 카운터를 장비별로 차분. 음수 증분은 리셋으로 보고 0 처리
  3. 야간 수집창(18~05시)만 남기고 업무일(경계 05시)에 귀속
  4. 하루 합계 + 피크 시각 + 장비 상태(팬 가동시간·배터리) 산출
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import DATA_RAW, PANEL_CSV, NIGHT_START, NIGHT_END


def load_raw() -> pd.DataFrame:
    d = pd.read_excel(DATA_RAW, sheet_name="raw_포집데이터")
    d.columns = ["station", "device", "region", "ts", "cum", "reset", "battery", "fan"]
    d["ts"] = pd.to_datetime(d["ts"])
    for c in ("station", "device", "region"):
        d[c] = d[c].astype(str).str.strip()
    d["is_reset"] = (d["reset"].astype(str).str.upper() == "Y").astype(int)
    # 원본 관측소명이 장비코드 접두 제거 과정에서 앞글자가 잘린 사례 보정
    # (예: 장비원본명 'HA023.1절기념체육관0015' -> 관측소명 '.1절기념체육관')
    d["station"] = d["station"].replace({".1절기념체육관": "3.1절기념체육관"})
    return d


def build_panel() -> pd.DataFrame:
    d = load_raw()
    n0 = len(d)

    # 1) 동일 시각 중복 전송 -> 누적 최대값 하나로
    d = (d.sort_values(["device", "ts", "cum"])
         .groupby(["device", "ts"], as_index=False)
         .agg(station=("station", "first"), region=("region", "first"),
              cum=("cum", "max"), is_reset=("is_reset", "max"),
              battery=("battery", "min"), fan=("fan", "max")))
    n_dup = n0 - len(d)

    # 2) 누적 -> 증분. 음수는 리셋/오류로 보고 0 처리(과소집계 가능성 감수)
    d = d.sort_values(["device", "ts"])
    d["inc"] = d.groupby("device")["cum"].diff()
    neg = d["inc"] < 0
    n_neg = int(neg.sum())
    n_neg_flagged = int((neg & (d["is_reset"] == 1)).sum())
    d.loc[neg, "inc"] = 0.0
    # 장비별 첫 관측은 직전값이 없어 증분 산출 불가 -> 제외
    d["inc"] = d["inc"].fillna(0.0)

    # 3) 야간 수집창만 사용, 업무일 귀속 (00~05시는 전날 업무일)
    hh = d["ts"].dt.hour
    night = d[(hh >= NIGHT_START) | (hh <= NIGHT_END)].copy()
    night["bizdate"] = np.where(
        night["ts"].dt.hour >= NIGHT_START,
        night["ts"].dt.normalize(),
        night["ts"].dt.normalize() - pd.Timedelta(days=1))
    night["bizdate"] = pd.to_datetime(night["bizdate"])

    # 4) 일별 집계 — 포집량 + 장비 상태
    g = night.groupby(["device", "station", "region", "bizdate"], as_index=False).agg(
        y=("inc", "sum"),
        n_meas=("inc", "size"),          # 그날 야간 측정 건수 (최대 12)
        fan_hours=("fan", "sum"),        # 팬 가동 시간 수 = 실제 포집 시도량
        battery=("battery", "mean"),
        n_reset=("is_reset", "sum"),
    )
    # 피크 시각
    idx = night.groupby(["device", "bizdate"])["inc"].idxmax()
    pk = night.loc[idx, ["device", "bizdate", "ts", "inc"]].copy()
    pk["peak_hour"] = np.where(pk["inc"] > 0, pk["ts"].dt.hour, -1)
    g = g.merge(pk[["device", "bizdate", "peak_hour"]], on=["device", "bizdate"], how="left")

    # 고유 ID: 장비명 기준(동명 관측소도 장비로 분리됨)
    g["sid"] = g["device"]

    # 관측소별 관측 시작~종료 사이 빠진 날짜를 명시적 결측으로 채움
    frames = []
    for sid, gg in g.groupby("sid", sort=False):
        gg = gg.sort_values("bizdate")
        full = pd.date_range(gg["bizdate"].min(), gg["bizdate"].max(), freq="D")
        gg = gg.set_index("bizdate").reindex(full)
        gg.index.name = "bizdate"
        gg["sid"] = sid
        for c in ("device", "station", "region"):
            gg[c] = gg[c].ffill().bfill()
        frames.append(gg.reset_index())
    panel = pd.concat(frames, ignore_index=True)

    panel["is_missing"] = panel["y"].isna().astype(int)
    # 장비가 돌지 않은 날(팬 가동 0시간)은 '실제 0'이 아니라 미작동으로 표시
    panel["device_off"] = ((panel["fan_hours"].fillna(0) == 0) &
                           (panel["y"].fillna(0) == 0)).astype(int)
    panel = panel.sort_values(["sid", "bizdate"]).reset_index(drop=True)

    obs = panel.groupby("sid")["y"].apply(lambda s: s.notna().sum())
    panel["n_obs_days"] = panel["sid"].map(obs)

    print(f"[전처리] RAW 측정 행수        : {n0:,}")
    print(f"[전처리] 동일시각 중복 제거    : {n_dup:,}행")
    print(f"[전처리] 음수 증분(롤백)       : {n_neg:,}건 "
          f"(리셋 플래그 있음 {n_neg_flagged:,} / 미플래그 {n_neg - n_neg_flagged:,}) -> 0 처리")
    print(f"[전처리] 야간 수집창 측정      : {len(night):,}행")
    print(f"[전처리] 고유 장비(관측소)     : {panel['sid'].nunique()}")
    print(f"[전처리] 권역                 : {panel['region'].nunique()}")
    print(f"[전처리] 패널 행수            : {len(panel):,} "
          f"(결측 삽입 {int(panel['is_missing'].sum()):,}행)")
    print(f"[전처리] 장비 미작동 추정일    : {int(panel['device_off'].sum()):,}일")
    print(f"[전처리] 기간                 : {panel['bizdate'].min():%Y-%m-%d} ~ "
          f"{panel['bizdate'].max():%Y-%m-%d}")
    print(f"[전처리] 60일 이상 관측소      : {(obs >= 60).sum()} / {len(obs)}")
    # ── moscom 일별값으로 y 교체 (웹사이트/ moscom.co.kr 과 통일) ──
    # 기존 y 는 raw 증분 차분값. moscom API 일별집계값으로 덮어써 사이트와 일치시킨다.
    from config import DATA_DIR
    ymap_path = DATA_DIR / "moscom_daily_y.csv"
    devmap_path = DATA_DIR / "dev_map.csv"
    if ymap_path.exists() and devmap_path.exists():
        dm = pd.read_csv(devmap_path, dtype=str)
        dm["device_name"] = dm["device_name"].fillna("").str.strip()
        ym = pd.read_csv(ymap_path, dtype={"device": str})
        ym["bizdate"] = pd.to_datetime(ym["bizdate"])
        # moscom device_uuid -> device_name(=panel의 device/station) 매핑
        uuid2name = dict(zip(dm["device_uuid"], dm["device_name"]))
        ym["dev_name"] = ym["device"].map(uuid2name)
        ym = ym.dropna(subset=["dev_name"])
        ykey = ym.set_index(["dev_name", "bizdate"])["y_moscom"]
        idx = list(zip(panel["device"].astype(str), panel["bizdate"]))
        new_y = pd.Series(idx, index=panel.index).map(lambda k: ykey.get(k, np.nan))
        matched = int(new_y.notna().sum())
        panel["y"] = new_y  # moscom 값 없는 (관측소,날짜)는 결측 처리
        panel["is_missing"] = panel["y"].isna().astype(int)
        print(f"[전처리] moscom 일별값으로 y 교체: {matched:,}행 매칭")

    # ── 이름이 숫자로만 된 관측소(미등록 신규 장비) 학습 제외 ──
    is_num = panel["station"].astype(str).str.fullmatch(r"\d+")
    n_num = panel.loc[is_num, "station"].nunique()
    panel = panel[~is_num].reset_index(drop=True)
    # 관측일수 재계산
    obs2 = panel.groupby("sid")["y"].apply(lambda s: s.notna().sum())
    panel["n_obs_days"] = panel["sid"].map(obs2)
    print(f"[전처리] 숫자이름 관측소 제외: {n_num}개 → 남은 관측소 {panel['sid'].nunique()}")

    print(f"[전처리] (최종) 하루 포집량 평균/최대  : {panel['y'].mean():.1f} / {panel['y'].max():.0f}")
    return panel


if __name__ == "__main__":
    p = build_panel()
    p.to_csv(PANEL_CSV, index=False, encoding="utf-8-sig")
    print(f"[저장] {PANEL_CSV}")
