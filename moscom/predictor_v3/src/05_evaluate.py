"""5단계: 성능 진단 및 시각화.

목적은 "몇 점인가"가 아니라 "어디서 쓸 수 있고 어디서 못 쓰는가"를 밝히는 것.
  - persistence 대비 이득의 관측소 단위 부트스트랩 신뢰구간
  - 발생 규모대(low/mid/high)별 성능 분해
  - 급증(스파이크) 탐지 능력 — 방제 의사결정에서 실제로 중요한 지표
"""
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import (FEATURES_CSV, OUT_DIR, HORIZONS, MIN_DAYS_EVAL,
                    VALID_DAYS, SEED)

warnings.filterwarnings("ignore")
exec(open(Path(__file__).parent / "04_train.py", encoding="utf-8")
     .read().split("def main()")[0])

for _f in ("Malgun Gothic", "AppleGothic", "NanumGothic"):
    if any(_f == f.name for f in matplotlib.font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = _f
        break
plt.rcParams["axes.unicode_minus"] = False


BEST_MODEL = {1: "Ridge", 2: "Ridge", 3: "RandomForest"}


def collect_predictions(df: pd.DataFrame, eval_sids: set) -> pd.DataFrame:
    """홀드아웃 구간에 대해 최적 모델과 베이스라인 예측을 모은다."""
    dmax = df["bizdate"].max()
    cut = dmax - pd.Timedelta(days=VALID_DAYS)
    frames = []
    for h in HORIZONS:
        tgt, dlt = f"target_h{h}", f"delta_h{h}"
        cols = feature_cols(df, h)
        d = df[df[tgt].notna() & df["y"].notna() & df[dlt].notna()]
        tr = d[d["bizdate"] <= cut]
        va = d[(d["bizdate"] > cut) & d["sid"].isin(eval_sids)].copy()

        mdl = make_models()[BEST_MODEL[h]]
        fit_weighted(mdl, tr[cols], tr[dlt].values, decay_weights(tr, cut))
        base = np.log1p(va["y"].values)
        va["pred"] = np.clip(np.expm1(base + mdl.predict(va[cols])), 0, None)
        va["persist"] = va["y"].values
        va["actual"] = va[tgt].values
        va["h"] = h
        frames.append(va[["sid", "station", "region", "bizdate", "h",
                          "actual", "pred", "persist", "y"]])
    return pd.concat(frames, ignore_index=True)


def sle(a, p):
    return (np.log1p(np.clip(p, 0, None)) - np.log1p(a)) ** 2


def bootstrap_gain(pred: pd.DataFrame, h: int, n_boot: int = 5000) -> tuple:
    """관측소 단위 부트스트랩으로 persistence 대비 이득의 신뢰구간."""
    s = pred[pred["h"] == h].copy()
    s["gain"] = sle(s["actual"], s["persist"]) - sle(s["actual"], s["pred"])
    per_st = s.groupby("sid")["gain"].mean().values
    rng = np.random.default_rng(SEED)
    boots = np.array([rng.choice(per_st, len(per_st), replace=True).mean()
                      for _ in range(n_boot)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return per_st.mean(), lo, hi, (per_st > 0).mean(), len(per_st)


def scale_breakdown(pred: pd.DataFrame, h: int) -> pd.DataFrame:
    """발생 규모대별 성능 분해."""
    s = pred[pred["h"] == h].copy()
    bins = [-0.1, 10, 50, 200, 1000, np.inf]
    labels = ["0~10", "11~50", "51~200", "201~1000", "1000+"]
    s["규모"] = pd.cut(s["y"], bins=bins, labels=labels)
    out = s.groupby("규모", observed=True).apply(lambda g: pd.Series({
        "n": len(g),
        "실제평균": g["actual"].mean(),
        "모델RMSLE": np.sqrt(sle(g["actual"], g["pred"]).mean()),
        "지속RMSLE": np.sqrt(sle(g["actual"], g["persist"]).mean()),
    }))
    out["개선(%)"] = (1 - out["모델RMSLE"] / out["지속RMSLE"]) * 100
    return out.reset_index()


def spike_detection(pred: pd.DataFrame, h: int, ratio: float = 2.0) -> dict:
    """급증(전일 대비 2배 이상) 탐지 성능. 방제 출동 판단에 직결되는 지표."""
    s = pred[(pred["h"] == h) & (pred["y"] >= 10)].copy()
    actual_spike = s["actual"] >= s["y"] * ratio
    pred_spike = s["pred"] >= s["y"] * ratio
    tp = int((actual_spike & pred_spike).sum())
    fp = int((~actual_spike & pred_spike).sum())
    fn = int((actual_spike & ~pred_spike).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"실제급증": int(actual_spike.sum()), "예측급증": int(pred_spike.sum()),
            "정탐": tp, "오탐": fp, "미탐": fn,
            "정밀도": prec, "재현율": rec, "F1": f1, "대상행": len(s)}


def make_plots(pred: pd.DataFrame, res: pd.DataFrame) -> None:
    # 1) 모델 비교 막대
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    ho = res[res["is_holdout"]]
    for ax, h in zip(axes, HORIZONS):
        sub = ho[ho["h"] == h].sort_values("R2_log")
        colors = ["#c44e52" if "Persistence" in m else
                  "#999999" if "Naive" in m else "#4c72b0" for m in sub["model"]]
        ax.barh(sub["model"], sub["R2_log"], color=colors)
        ax.set_title(f"h = {h}일 앞 (로그공간 R², 높을수록 우수)")
        ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "01_model_comparison.png", dpi=130)
    plt.close()

    # 2) 관측소별 이득 분포
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for ax, h in zip(axes, HORIZONS):
        s = pred[pred["h"] == h].copy()
        s["gain"] = sle(s["actual"], s["persist"]) - sle(s["actual"], s["pred"])
        g = s.groupby("sid")["gain"].mean().sort_values()
        ax.barh(range(len(g)), g.values,
                color=["#55a868" if v > 0 else "#c44e52" for v in g.values])
        ax.axvline(0, color="k", lw=1)
        ax.set_title(f"h={h}: 관측소별 persistence 대비 이득\n"
                     f"(양수=모델 우수, {(g > 0).mean() * 100:.0f}%만 우수)")
        ax.set_yticks([])
        ax.set_xlabel("평균 제곱로그오차 감소량")
        ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "02_station_gain.png", dpi=130)
    plt.close()

    # 3) 실제 vs 예측 산점도
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, h in zip(axes, HORIZONS):
        s = pred[pred["h"] == h]
        ax.scatter(s["actual"] + 1, s["pred"] + 1, s=12, alpha=0.35, color="#4c72b0")
        lim = [1, max(s["actual"].max(), s["pred"].max()) * 1.2]
        ax.plot(lim, lim, "r--", lw=1)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("실제 (마리+1)"); ax.set_ylabel("예측 (마리+1)")
        ax.set_title(f"h = {h}일 앞")
        ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "03_pred_vs_actual.png", dpi=130)
    plt.close()

    # 4) 상위 관측소 시계열
    top = (pred[pred["h"] == 1].groupby(["sid", "station"])["actual"]
           .mean().sort_values(ascending=False).head(6))
    fig, axes = plt.subplots(3, 2, figsize=(15, 9), sharex=True)
    for ax, (sid, st) in zip(axes.ravel(), top.index):
        s = pred[(pred["h"] == 1) & (pred["sid"] == sid)].sort_values("bizdate")
        ax.plot(s["bizdate"], s["actual"], "o-", ms=3, label="실제", color="#333")
        ax.plot(s["bizdate"], s["pred"], "s--", ms=3, label="모델", color="#4c72b0")
        ax.plot(s["bizdate"], s["persist"], "^:", ms=3, label="지속", color="#c44e52")
        ax.set_title(st, fontsize=10)
        ax.grid(alpha=0.3)
        ax.tick_params(axis="x", labelrotation=30)
    axes[0, 0].legend(fontsize=8)
    plt.suptitle("발생량 상위 관측소 · 홀드아웃 구간 h=1 예측", y=1.00)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "04_timeseries_top.png", dpi=130)
    plt.close()
    print(f"[저장] 그래프 4종 -> {OUT_DIR}")


def main() -> None:
    df = pd.read_csv(FEATURES_CSV, parse_dates=["bizdate"])
    for h in HORIZONS:
        df[f"delta_h{h}"] = np.log1p(df[f"target_h{h}"]) - np.log1p(df["y"])
    eval_sids = set(df.loc[df["n_obs_days"] >= MIN_DAYS_EVAL, "sid"].unique())

    pred = collect_predictions(df, eval_sids)
    pred.to_csv(OUT_DIR / "holdout_predictions.csv", index=False, encoding="utf-8-sig")

    print("=" * 78)
    print("0. 정확도 지표 요약 (홀드아웃)")
    print("=" * 78)
    print(f"{'h':>3} {'모델':>14} {'R²(로그)':>10} {'R²(원공간)':>11} "
          f"{'RMSLE':>8} {'RMSE':>9} {'MAE':>8}")
    for h in HORIZONS:
        s = pred[pred["h"] == h]
        a, p, pe = s["actual"].values, s["pred"].values, s["persist"].values
        for label, q in (("모델", p), ("지속(기준)", pe)):
            la, lq = np.log1p(a), np.log1p(np.clip(q, 0, None))
            name = BEST_MODEL[h] if label == "모델" else "Persistence"
            print(f"{h:>3} {name:>14} {_r2(la, lq):>+10.4f} {_r2(a, q):>+11.4f} "
                  f"{np.sqrt(np.mean((lq - la) ** 2)):>8.4f} "
                  f"{np.sqrt(np.mean((q - a) ** 2)):>9.1f} "
                  f"{np.mean(np.abs(q - a)):>8.1f}")

    print("\n" + "=" * 78)
    print("1. persistence 대비 이득의 통계적 유의성 (관측소 단위 부트스트랩)")
    print("=" * 78)
    for h in HORIZONS:
        mean, lo, hi, win, n = bootstrap_gain(pred, h)
        verdict = "유의함 ***" if lo > 0 else "유의하지 않음 (구간이 0을 포함)"
        print(f"  h={h}: 평균이득 {mean:+.4f}  95%CI [{lo:+.4f}, {hi:+.4f}]  "
              f"우세 관측소 {win * 100:.0f}%/{n}개  -> {verdict}")

    print("\n" + "=" * 78)
    print("1-2. 극단값 민감도 (실제 상위 3건 제외 시 R² 변화)")
    print("=" * 78)
    for h in HORIZONS:
        s = pred[pred["h"] == h]
        a, p = s["actual"].values, s["pred"].values
        k = np.argsort(a)[:-3]
        print(f"  h={h}: 로그 R² {_r2(np.log1p(a), np.log1p(p)):+.4f} -> "
              f"{_r2(np.log1p(a[k]), np.log1p(p[k])):+.4f}   |   "
              f"원공간 R² {_r2(a, p):+.4f} -> {_r2(a[k], p[k]):+.4f}")

    print("\n" + "=" * 78)
    print("2. 발생 규모대별 성능 분해 (h=1)")
    print("=" * 78)
    for h in HORIZONS:
        print(f"\n■ h = {h}")
        print(scale_breakdown(pred, h).to_string(
            index=False, float_format=lambda v: f"{v:8.2f}"))

    print("\n" + "=" * 78)
    print("3. 급증 탐지 성능 (전일 대비 2배 이상, 기준일 10마리 이상 구간)")
    print("=" * 78)
    for h in HORIZONS:
        r = spike_detection(pred, h)
        print(f"  h={h}: 실제급증 {r['실제급증']:3d}건 / 대상 {r['대상행']:4d}행 · "
              f"정탐 {r['정탐']:3d} 오탐 {r['오탐']:3d} 미탐 {r['미탐']:3d} · "
              f"정밀도 {r['정밀도']:.2f} 재현율 {r['재현율']:.2f} F1 {r['F1']:.2f}")

    res = pd.read_csv(OUT_DIR / "model_comparison_raw.csv")
    make_plots(pred, res)


if __name__ == "__main__":
    main()
