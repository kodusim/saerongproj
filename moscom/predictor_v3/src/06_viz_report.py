"""6단계: 발표용 시각화 생성.

산출
  05_metrics_r2_rmse.png    R2 / RMSE 지표 비교
  06_feature_importance.png 순열 중요도(permutation importance) 상위 피처
  07_station_6.png          관측소 6개 실제 vs 예측 시계열
  08_scale_breakdown.png    규모대별 개선율
"""
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

sys.path.insert(0, str(Path(__file__).parent))
from config import FEATURES_CSV, OUT_DIR, HORIZONS, MIN_DAYS_EVAL, VALID_DAYS, SEED

warnings.filterwarnings("ignore")
exec(open(Path(__file__).parent / "04_train.py", encoding="utf-8")
     .read().split("def main()")[0])

for _f in ("Malgun Gothic", "AppleGothic", "NanumGothic"):
    if any(_f == f.name for f in matplotlib.font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = _f
        break
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.25

BEST_MODEL = {1: "Ridge", 2: "Ridge", 3: "RandomForest"}
BLUE, RED, GRAY = "#2E5C8A", "#C0504D", "#A6A6A6"

# 피처 한글 라벨 (발표용)
LABEL = {
    "lag1": "1일 전 포집량", "lag2": "2일 전", "lag3": "3일 전", "lag4": "4일 전",
    "lag5": "5일 전", "lag6": "6일 전", "lag7": "7일 전",
    "roll3_mean": "최근 3일 평균", "roll7_mean": "최근 7일 평균",
    "roll3_max": "최근 3일 최대", "roll7_max": "최근 7일 최대",
    "roll3_std": "최근 3일 변동", "roll7_std": "최근 7일 변동",
    "trend_3v7": "단기-중기 추세차", "diff1": "전일 대비 변화", "diff2": "전전일 대비 변화",
    "z_vs_own14": "평소 대비 편차(z)", "ratio_vs_own14": "평소 대비 배율",
    "own_vol14": "자체 변동성(14일)", "own_vol7": "자체 변동성(7일)",
    "region_daymean": "권역 동시 수준", "region_dev": "권역 대비 편차",
    "region_diff1": "권역 전일 변화", "region_diff3": "권역 3일 변화",
    "net_diff1": "전국 전일 변화", "net_diff3": "전국 3일 변화",
    "obs_ratio7": "최근 관측 충실도", "zero_ratio7": "최근 무발생 비율",
    "sid_code": "관측소 ID", "region_code": "권역 ID",
    "w_temperature_2m_mean_d0": "당일 평균기온", "w_night_temp_d0": "야간 평균기온",
    "w_night_humid_d0": "야간 습도", "w_night_precip_d0": "야간 강수",
    "w_precip_7": "7일 누적강수", "w_precip_14": "14일 누적강수",
    "w_precip_lag3_10": "3~10일전 누적강수", "w_days_since_rain": "무강수 경과일",
    "w_night_wind_d0": "야간 풍속", "w_temperature_2m_max_d0": "당일 최고기온",
    "w_temperature_2m_min_d0": "당일 최저기온",
}


def nice(c: str) -> str:
    if c in LABEL:
        return LABEL[c]
    c2 = c.replace("w_", "").replace("_d0", "(당일)").replace("_lag1", "(1일전)")
    c2 = c2.replace("_m3", "(3일평균)").replace("_m7", "(7일평균)")
    c2 = (c2.replace("temperature_2m_mean", "평균기온")
            .replace("temperature_2m_max", "최고기온")
            .replace("temperature_2m_min", "최저기온")
            .replace("precipitation_sum", "강수량").replace("night_temp_min", "야간최저기온")
            .replace("night_temp", "야간기온").replace("night_humid", "야간습도")
            .replace("night_precip", "야간강수").replace("night_wind", "야간풍속"))
    for h in HORIZONS:
        c2 = c2.replace(f"dow_h{h}", "요일").replace(f"is_weekend_h{h}", "주말여부")
    return c2


def fit_and_predict(df, h, cut, eval_sids):
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
    return mdl, cols, tr, va


def plot_metrics(df, eval_sids, cut):
    """R2 / RMSE 지표 비교."""
    rows = []
    for h in HORIZONS:
        _, _, _, va = fit_and_predict(df, h, cut, eval_sids)
        a, p, pe = va["actual"].values, va["pred"].values, va["persist"].values
        la, lp, lpe = np.log1p(a), np.log1p(p), np.log1p(pe)
        rows.append({"h": h,
                     "R2m": _r2(la, lp), "R2p": _r2(la, lpe),
                     "RMSEm": np.sqrt(np.mean((p - a) ** 2)),
                     "RMSEp": np.sqrt(np.mean((pe - a) ** 2)),
                     "RMSLEm": np.sqrt(np.mean((lp - la) ** 2)),
                     "RMSLEp": np.sqrt(np.mean((lpe - la) ** 2))})
    r = pd.DataFrame(rows)
    x = np.arange(len(HORIZONS)); w = 0.36

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    specs = [("R2m", "R2p", "결정계수 R² (로그공간)", "높을수록 우수", False),
             ("RMSLEm", "RMSLEp", "RMSLE (로그공간 오차)", "낮을수록 우수", True),
             ("RMSEm", "RMSEp", "RMSE (마리)", "낮을수록 우수", True)]
    for ax, (mk, pk, title, sub, lower) in zip(axes, specs):
        b1 = ax.bar(x - w / 2, r[mk], w, label="예측 모델", color=BLUE)
        b2 = ax.bar(x + w / 2, r[pk], w, label="기준선(전일값)", color=GRAY)
        for b in list(b1) + list(b2):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                    f"{b.get_height():.3f}" if not lower or b.get_height() < 10
                    else f"{b.get_height():.0f}",
                    ha="center", va="bottom", fontsize=9)
        ax.set_xticks(x); ax.set_xticklabels([f"{h}일 후" for h in HORIZONS])
        ax.set_title(f"{title}\n({sub})", fontsize=11)
        ax.legend(fontsize=9)
        ax.margins(y=0.18)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "05_metrics_r2_rmse.png", dpi=150, bbox_inches="tight")
    plt.close()
    return r


def plot_importance(df, eval_sids, cut, h=1, topn=15):
    """순열 중요도 — 실제 예측 성능 기여를 직접 측정."""
    mdl, cols, tr, va = fit_and_predict(df, h, cut, eval_sids)
    dlt = f"delta_h{h}"
    imp = permutation_importance(mdl, va[cols], va[dlt].values,
                                 n_repeats=10, random_state=SEED, n_jobs=-1)
    s = (pd.DataFrame({"f": cols, "v": imp.importances_mean})
         .sort_values("v", ascending=False).head(topn).iloc[::-1])

    def cat_color(f):
        if f.startswith(("region_", "net_")):
            return "#D9822B"       # 동시성
        if f.startswith("w_"):
            return "#4E9F50"       # 기상
        return BLUE                # 자기 이력

    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    ax.barh([nice(f) for f in s["f"]], s["v"], color=[cat_color(f) for f in s["f"]])
    ax.set_xlabel("중요도 (제거 시 성능 저하폭)")
    ax.set_title(f"예측 기여도 상위 {topn}개 (h=1일 후)", fontsize=12)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in [BLUE, "#D9822B", "#4E9F50"]]
    ax.legend(handles, ["자기 관측 이력", "권역·전국 동시성", "기상"],
              loc="lower right", fontsize=9)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "06_feature_importance.png", dpi=150, bbox_inches="tight")
    plt.close()
    return s


def plot_stations(df, eval_sids, cut, n=6):
    """관측소 6개 실제 vs 예측.

    선정 기준: 이름이 등록된 관측소 중 발생 규모가 서로 다른 6곳을
    '대표성' 기준으로 고른다. 성능 상위만 고르면 과대 포장이 되고,
    무작위로 고르면 극단 사례가 섞이므로, 규모 구간별로 성능이
    중앙값에 가까운 관측소를 하나씩 선택한다.
    """
    _, _, _, va = fit_and_predict(df, 1, cut, eval_sids)
    # 이름 미등록 장비(전체가 숫자 코드인 경우)만 제외.
    # '3.1절기념체육관'처럼 숫자로 시작하는 정상 이름은 남긴다.
    named = va[~va["station"].str.fullmatch(r"\d+.*sugwang|\d+")].copy()

    stat = named.groupby(["sid", "station"]).apply(
        lambda g: pd.Series({
            "mean": g["actual"].mean(),
            "r2": _r2(np.log1p(g["actual"].values), np.log1p(g["pred"].values)),
        }), include_groups=False).reset_index()

    # 발생 규모 4구간으로 나눠 각 구간에서 R2 중앙값에 가까운 관측소 선택
    stat = stat.sort_values("mean", ascending=False)
    bands = np.array_split(stat, n)
    pick = []
    for b in bands:
        if len(b) == 0:
            continue
        med = b["r2"].median()
        row = b.iloc[(b["r2"] - med).abs().argsort().iloc[0]]
        pick.append((row["sid"], row["station"]))
    pick = pick[:n]

    fig, axes = plt.subplots(2, 3, figsize=(16, 7.5))
    for ax, (sid, st) in zip(axes.ravel(), pick):
        s = va[va["sid"] == sid].sort_values("bizdate")
        ax.plot(s["bizdate"], s["actual"], "o-", ms=4, lw=1.8, color="#333", label="실제")
        ax.plot(s["bizdate"], s["pred"], "s--", ms=4, lw=1.8, color=BLUE, label="예측")
        a, p = s["actual"].values, s["pred"].values
        # 관측소 단위 R²는 21일 내 분산이 작아 과도하게 나빠 보이므로,
        # 해석이 직관적인 평균 오차(마리)를 표기한다. 전체 R²는 별도 슬라이드에.
        ax.set_title(f"{st}   (일 평균 {a.mean():,.0f}마리 · 평균오차 {np.abs(p - a).mean():,.0f}마리)",
                     fontsize=10.5)
        ax.tick_params(axis="x", labelrotation=25, labelsize=8)
        ax.tick_params(axis="y", labelsize=8)
    axes[0, 0].legend(fontsize=10)
    # 슬라이드 제목과 중복되므로 그림 자체 제목은 넣지 않는다
    plt.tight_layout()
    plt.savefig(OUT_DIR / "07_station_6.png", dpi=150, bbox_inches="tight")
    plt.close()
    return pick


def plot_scale(df, eval_sids, cut):
    """규모대별 개선율."""
    bins = [-0.1, 10, 50, 200, 1000, np.inf]
    labels = ["0~10", "11~50", "51~200", "201~1000", "1000+"]
    fig, ax = plt.subplots(figsize=(9.5, 5))
    x = np.arange(len(labels)); w = 0.26
    for i, h in enumerate(HORIZONS):
        _, _, _, va = fit_and_predict(df, h, cut, eval_sids)
        va["g"] = pd.cut(va["y"], bins=bins, labels=labels)
        imp = []
        for lb in labels:
            s = va[va["g"] == lb]
            if len(s) == 0:
                imp.append(0); continue
            m = np.sqrt(np.mean((np.log1p(s["pred"]) - np.log1p(s["actual"])) ** 2))
            p = np.sqrt(np.mean((np.log1p(s["persist"]) - np.log1p(s["actual"])) ** 2))
            imp.append((1 - m / p) * 100)
        ax.bar(x + (i - 1) * w, imp, w, label=f"{h}일 후",
               color=[BLUE, "#5B8FC7", "#9DBDDE"][i])
    ax.axhline(0, color="k", lw=1)
    ax.set_xticks(x); ax.set_xticklabels([f"{l}마리" for l in labels])
    ax.set_ylabel("기준선 대비 개선율 (%)")
    ax.set_title("발생 규모대별 개선율 — 양수일수록 모델이 우수", fontsize=12)
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "08_scale_breakdown.png", dpi=150, bbox_inches="tight")
    plt.close()


def main():
    df = pd.read_csv(FEATURES_CSV, parse_dates=["bizdate"])
    for h in HORIZONS:
        df[f"delta_h{h}"] = np.log1p(df[f"target_h{h}"]) - np.log1p(df["y"])
    eval_sids = set(df.loc[df["n_obs_days"] >= MIN_DAYS_EVAL, "sid"].unique())
    cut = df["bizdate"].max() - pd.Timedelta(days=VALID_DAYS)

    r = plot_metrics(df, eval_sids, cut)
    print("[1/4] 지표 그래프 완료")
    print(r.to_string(index=False, float_format=lambda v: f"{v:8.3f}"))
    s = plot_importance(df, eval_sids, cut)
    print("\n[2/4] 중요도 그래프 완료 — 상위 5개")
    print(s.iloc[::-1].head(5).to_string(index=False))
    pick = plot_stations(df, eval_sids, cut)
    print(f"\n[3/4] 관측소 그래프 완료 — {[p[1] for p in pick]}")
    plot_scale(df, eval_sids, cut)
    print("[4/4] 규모대별 그래프 완료")
    print(f"\n[저장] {OUT_DIR}")


if __name__ == "__main__":
    main()
