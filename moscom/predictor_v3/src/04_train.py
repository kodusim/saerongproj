"""4단계: 모델 학습 및 비교 (h = 1, 2, 3일 앞).

■ 핵심 설계: 절대량이 아닌 '변화량(Δ)'을 학습한다
  단일 시즌 105일 데이터에서 절대 수준을 직접 회귀하면, 모델이 달력·적산온도
  피처로부터 "시즌이 갈수록 증가"라는 추세를 학습해 검증 구간(성수기)에서
  과대예측한다. 실제로 절대량 회귀 시 로그공간 편향이 +0.60 (약 1.8배 과대),
  45개 관측소 전부에서 persistence 에 패배했다.
  -> 타깃을 Δ = log1p(y_{d+h}) - log1p(y_d) 로 두어 persistence 를 기본값으로
     삼고, 모델은 그로부터의 편차만 학습한다. 예측은 log1p(y_d) + Δ̂ 로 복원.

검증 설계
  - 시간 순서 유지. 마지막 VALID_DAYS(21일)를 홀드아웃으로 사용.
  - 확장창(expanding window) 3-fold 백테스트로 단일 홀드아웃의 우연 배제.
  - 평가는 유효 관측 60일 이상 관측소만 (학습에는 전체 사용).
  - 지표는 원공간(마리수) 기준. persistence 대비 개선율(Skill)을 함께 보고.
"""
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

import lightgbm as lgb
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).parent))
from config import (FEATURES_CSV, MODEL_DIR, OUT_DIR, HORIZONS,
                    MIN_DAYS_EVAL, VALID_DAYS, SEED)

warnings.filterwarnings("ignore")

EXCLUDE = {"sid", "station", "region", "bizdate", "y", "peak_hour", "n_obs_days",
           "n_dev", "date"}
# 시즌 추세를 그대로 외삽시키는 피처는 Δ 모델에서 제외
#   - doy/month: 단일 시즌이라 '연중일 = 증가' 를 그대로 암기
#   - days_since_start, sid_expmean, 누적 GDD: 동일한 단조 증가 신호
TREND_LEAK = ("doy_h", "month_h", "days_since_start", "sid_expmean",
              "w_gdd_7", "w_gdd_14")


def feature_cols(df: pd.DataFrame, h: int, drop_trend: bool = True) -> list:
    """h 시점 예측에 쓸 컬럼. 다른 h의 타깃/달력 컬럼은 제외."""
    cols = []
    for c in df.columns:
        if c in EXCLUDE or c.startswith(("target_h", "persist_h", "delta_h")):
            continue
        if "_h" in c and c.split("_h")[-1].isdigit() and not c.endswith(f"_h{h}"):
            continue
        if drop_trend and c.startswith(TREND_LEAK):
            continue
        if df[c].dtype.kind not in "ifb":
            continue
        cols.append(c)
    return cols


def _r2(a: np.ndarray, p: np.ndarray) -> float:
    ss_res = np.sum((a - p) ** 2)
    ss_tot = np.sum((a - a.mean()) ** 2)
    return 1 - ss_res / ss_tot if ss_tot > 0 else np.nan


def metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true, float)
    y_pred = np.clip(np.asarray(y_pred, float), 0, None)
    err = y_pred - y_true
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2
    la, lp = np.log1p(y_true), np.log1p(y_pred)
    return {
        "R2_log": _r2(la, lp),      # 주 지표: 규모 편중이 없는 로그공간 결정계수
        "RMSLE": np.sqrt(np.mean((lp - la) ** 2)),
        "R2_raw": _r2(y_true, y_pred),   # 참고: 극단값 소수가 지배하므로 해석 주의
        "RMSE": np.sqrt(np.mean(err ** 2)),
        "MAE": np.mean(np.abs(err)),
        "sMAPE": np.mean(np.where(denom > 0, np.abs(err) / np.where(denom > 0, denom, 1), 0)) * 100,
    }


def make_models(seed: int = SEED) -> dict:
    """Δ 학습용. 잔차는 신호 대비 잡음이 크므로 강하게 규제한다.

    규제 강도는 로그공간 R2 기준 3-fold 그리드 탐색으로 정했다.
    (예: LGBM num_leaves 31->7, reg_lambda 5->100 으로 갈수록 단조 개선)
    """
    return {
        "Ridge": make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=500.0)),
        "RandomForest": make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestRegressor(n_estimators=500, min_samples_leaf=20,
                                  max_features=0.4, n_jobs=-1, random_state=seed)),
        "XGBoost": xgb.XGBRegressor(
            n_estimators=400, learning_rate=0.02, max_depth=3,
            subsample=0.8, colsample_bytree=0.6, min_child_weight=60,
            reg_lambda=50.0, n_jobs=-1, random_state=seed, verbosity=0),
        "LightGBM": lgb.LGBMRegressor(
            n_estimators=400, learning_rate=0.02, num_leaves=7,
            min_child_samples=100, subsample=0.8, subsample_freq=1,
            colsample_bytree=0.6, reg_lambda=100.0, n_jobs=-1,
            random_state=seed, verbose=-1),
    }


def decay_weights(tr: pd.DataFrame, cut: pd.Timestamp, halflife: int = 21) -> np.ndarray:
    """최근 데이터에 더 큰 가중. 시즌 진행에 따른 개체 동태 변화를 반영."""
    age = (cut - tr["bizdate"]).dt.days.values
    return 0.5 ** (age / halflife)


def fit_weighted(mdl, X, y, w):
    """Pipeline / 단일 추정기 모두에 sample_weight 를 전달."""
    if hasattr(mdl, "steps"):
        return mdl.fit(X, y, **{f"{mdl.steps[-1][0]}__sample_weight": w})
    return mdl.fit(X, y, sample_weight=w)


def run_split(df: pd.DataFrame, h: int, cut: pd.Timestamp,
              eval_sids: set, fit_final: bool = False) -> tuple:
    """cut 이전으로 학습, cut 이후를 검증."""
    tgt, dlt = f"target_h{h}", f"delta_h{h}"
    cols = feature_cols(df, h)
    d = df[df[tgt].notna() & df["y"].notna() & df[dlt].notna()].copy()

    tr = d[d["bizdate"] <= cut]
    va = d[(d["bizdate"] > cut) & d["sid"].isin(eval_sids)]
    if len(tr) < 200 or len(va) < 30:
        return [], {}

    Xtr, Xva = tr[cols], va[cols]
    yva = va[tgt].values
    base_va = np.log1p(va["y"].values)   # persistence 기준선 (log 공간)

    rows, fitted = [], {}
    rows.append({"model": "Persistence(기준값유지)", **metrics(yva, va[f"persist_h{h}"].values)})
    rows.append({"model": "Naive(최근3일평균)",
                 **metrics(yva, np.expm1(va["roll3_mean"].fillna(0).values))})

    w = decay_weights(tr, cut)
    for name, mdl in make_models().items():
        fit_weighted(mdl, Xtr, tr[dlt].values, w)      # Δ 학습 (최근 가중)
        pred = np.expm1(base_va + mdl.predict(Xva))    # 기준선 + Δ̂ 복원
        rows.append({"model": name, **metrics(yva, pred)})
        if fit_final:
            fitted[name] = mdl
    return rows, fitted


def main() -> None:
    df = pd.read_csv(FEATURES_CSV, parse_dates=["bizdate"])
    # Δ 타깃 생성: log1p(y_{d+h}) - log1p(y_d)
    for h in HORIZONS:
        df[f"delta_h{h}"] = np.log1p(df[f"target_h{h}"]) - np.log1p(df["y"])

    eval_sids = set(df.loc[df["n_obs_days"] >= MIN_DAYS_EVAL, "sid"].unique())
    print(f"[평가대상] {len(eval_sids)}개 관측소 (유효 관측 {MIN_DAYS_EVAL}일 이상) "
          f"/ 전체 {df['sid'].nunique()}개")
    print("[학습] 전체 관측소 사용 · 타깃 = Δlog(변화량)\n")

    dmax = df["bizdate"].max()
    holdout_cut = dmax - pd.Timedelta(days=VALID_DAYS)
    folds = [dmax - pd.Timedelta(days=VALID_DAYS * k) for k in (3, 2, 1)]

    all_rows, final_models = [], {}
    for h in HORIZONS:
        for fi, cut in enumerate(folds, 1):
            rows, fitted = run_split(df, h, cut, eval_sids,
                                     fit_final=(cut == holdout_cut))
            for r in rows:
                r.update({"h": h, "fold": fi, "cut": cut.strftime("%Y-%m-%d"),
                          "is_holdout": cut == holdout_cut})
                all_rows.append(r)
            if fitted:
                final_models[h] = fitted

    res = pd.DataFrame(all_rows)
    res.to_csv(OUT_DIR / "model_comparison_raw.csv", index=False, encoding="utf-8-sig")

    print("=" * 80)
    print(f"홀드아웃 검증 ({(holdout_cut + pd.Timedelta(days=1)):%Y-%m-%d} ~ {dmax:%Y-%m-%d}, "
          f"최근 {VALID_DAYS}일)")
    print("=" * 80)
    ho = res[res["is_holdout"]]
    for h in HORIZONS:
        sub = ho[ho["h"] == h].copy()
        base = sub.loc[sub["model"].str.startswith("Persistence"), "R2_log"].iloc[0]
        sub["ΔR2_log"] = sub["R2_log"] - base
        print(f"\n■ h = {h}일 앞 예측  (기준선 persistence R2_log = {base:+.4f})")
        print(sub.sort_values("R2_log", ascending=False)[
            ["model", "R2_log", "ΔR2_log", "RMSLE", "R2_raw", "RMSE", "MAE"]]
              .to_string(index=False,
                         formatters={"R2_log": "{:+8.4f}".format,
                                     "ΔR2_log": "{:+9.4f}".format,
                                     "RMSLE": "{:7.4f}".format,
                                     "R2_raw": "{:+8.4f}".format,
                                     "RMSE": "{:9.1f}".format, "MAE": "{:8.1f}".format}))

    print("\n" + "=" * 80)
    print("확장창 백테스트 3-fold 평균 로그공간 R² (높을수록 우수)")
    print("=" * 80)
    piv = res.pivot_table(index="model", columns="h", values="R2_log", aggfunc="mean")
    piv["평균"] = piv.mean(axis=1)
    print(piv.sort_values("평균", ascending=False)
          .to_string(float_format=lambda v: f"{v:+7.4f}"))

    for h, mdls in final_models.items():
        sub = ho[(ho["h"] == h) & (~ho["model"].str.contains("Persistence|Naive"))]
        best = sub.sort_values("R2_log", ascending=False)["model"].iloc[0]
        joblib.dump({"model": mdls[best], "features": feature_cols(df, h),
                     "name": best, "horizon": h, "target": "delta_log"},
                    MODEL_DIR / f"best_h{h}.joblib")
        print(f"[저장] h={h} 최적: {best} -> models/best_h{h}.joblib")


if __name__ == "__main__":
    main()
