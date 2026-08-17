"""TDM 예측 v2 — 환자군 4분류(Adult/AdultHD/Pediatric/PediatricHD) 별 XGBoost.

출처: OneDrive 농도예측3/only_Machine_model_patient (model_result/{group}/{target}_xgboost.joblib)
모델 파일: tdm/ml_artifacts_v2/{group}/{target}_xgboost.joblib (gitignore — 서버 별도 scp)

타겟 5종: dose_mg, EstimatedPeak, EstimatedTrough, AUC, target_concentration
joblib 번들 구조: {'pipeline': sklearn Pipeline, 'features': [...], 'target': str, 'model': str}

농도 곡선: 이 모델은 사이클 단위 포인트 예측(Peak/Trough)만 내놓으므로, 사이클 순번(1..n_doses)을
바꿔가며 반복 예측한 뒤 표준 1-compartment 정상상태 공식(제거속도상수 k_e를 그 사이클의
Peak/Trough 예측값에서 역산 → C(t)=Peak·exp(-k_e·t) 감쇠)으로 시간축 곡선을 재구성한다.
(초기 구현은 Hybrid_model_2cm_bs_pipet의 build_landmark_curve()를 그대로 이식해 임의 지수계수를
썼으나, 약동학적 근거가 없어 1-compartment 역산 공식으로 교체함 — _landmark_curve() 참고.)

Lazy load + lru_cache. 첫 요청 때만 그룹×타겟 조합을 로드.
"""
from __future__ import annotations
import json
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

ART_DIR = os.path.join(os.path.dirname(__file__), 'ml_artifacts_v2')
GROUPS = ['Adult', 'AdultHD', 'Pediatric', 'PediatricHD']
TARGETS = ['dose_mg', 'EstimatedPeak', 'EstimatedTrough', 'AUC', 'target_concentration']
PEDIATRIC_AGE_CUTOFF_YEARS = 18.0

# concentration_model_dataset 학습 시 중앙값 기반 기본값 — 폼에서 받지 않는 검사값.
DEFAULTS = {
    'Diagnosis': None, 'SuspectedSymptom': None, 'DoseIntervalHr': None,
    'CycleSequence': 1.0, 'DosesPerDay': 2.0,
    'RBC': 3.24, 'Hb': 9.6, 'Hct': 29.4,
    'ANC': None, 'Ca': None, 'Phos': None, 'UricAcid': None, 'TotalProtein': None,
    'TotalBilirubin': None, 'AlkPhos': None, 'TCO2': None, 'PKS_CL': None,
    'BUN': 16.0, 'Na': 138.0, 'K': 4.0, 'Cl': 102.0,
}


@lru_cache(maxsize=1)
def _load_metrics() -> dict:
    path = os.path.join(ART_DIR, 'metrics.json')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


@lru_cache(maxsize=32)
def _load_bundle(group: str, target: str):
    import joblib
    path = os.path.join(ART_DIR, group, f'{target}_xgboost.joblib')
    if not os.path.exists(path):
        raise FileNotFoundError(f'TDM v2 모델 파일 누락: {path}')
    bundle = joblib.load(path)
    return bundle['pipeline'], bundle['features']


def _calc_bmi(weight_kg, height_cm):
    if not weight_kg or not height_cm:
        return None
    h_m = height_cm / 100.0
    return round(weight_kg / (h_m * h_m), 2)


def _calc_bsa(weight_kg, height_cm):
    """Mosteller BSA (m^2)."""
    if not weight_kg or not height_cm:
        return None
    return round(((weight_kg * height_cm) / 3600.0) ** 0.5, 3)


def _crcl_cockcroft_gault(age, sex, weight_kg, scr_mgdl):
    """Cockcroft-Gault CrCL (mL/min). sex: 1=남성, 0=여성."""
    if not all([age, weight_kg, scr_mgdl]) or scr_mgdl <= 0:
        return None
    crcl = ((140 - age) * weight_kg) / (72 * scr_mgdl)
    if sex == 0:
        crcl *= 0.85
    return round(crcl, 1)


def _egfr_ckd_epi(age, sex, scr_mgdl):
    """CKD-EPI 2021 (race-free) 근사. sex: 1=남성, 0=여성."""
    if not all([age, scr_mgdl]) or scr_mgdl <= 0:
        return None
    is_female = (sex == 0)
    kappa = 0.7 if is_female else 0.9
    alpha = -0.241 if is_female else -0.302
    scr_k = scr_mgdl / kappa
    egfr = (
        142
        * min(scr_k, 1.0) ** alpha
        * max(scr_k, 1.0) ** -1.200
        * (0.9938 ** age)
        * (1.012 if is_female else 1.0)
    )
    return round(egfr, 1)


def classify_group(age_years: float, is_hd: bool) -> str:
    age_group = 'Pediatric' if age_years < PEDIATRIC_AGE_CUTOFF_YEARS else 'Adult'
    if is_hd:
        return 'AdultHD' if age_group == 'Adult' else 'PediatricHD'
    return age_group


def _build_patient_context(patient: dict) -> dict:
    """환자 입력 → 산출 covariate. cycle에 무관한 값들만 계산."""
    def f(key, default):
        v = patient.get(key)
        return float(v) if v not in (None, '') else float(default)

    age = f('age', 0)
    sex_raw = patient.get('sex')
    sex = int(sex_raw) if sex_raw not in (None, '') else 1
    height = f('height', 170)
    weight = f('weight', 65)
    is_hd = bool(patient.get('is_hd', False))
    scr = f('Serum_Cr', 1.0)

    crcl = patient.get('CrCL_mL_per_min')
    if crcl in (None, '') or float(crcl) <= 0:
        crcl = _crcl_cockcroft_gault(age, sex, weight, scr) or 75.6
    crcl = float(crcl)

    bmi = _calc_bmi(weight, height) or 24.0
    bsa = _calc_bsa(weight, height) or 1.57
    egfr = _egfr_ckd_epi(age, sex, scr) or 96.3
    albumin = f('Albumin', 3.1)

    group = classify_group(age, is_hd)
    age_group = 'Pediatric' if age < PEDIATRIC_AGE_CUTOFF_YEARS else 'Adult'
    remark_label = 'POS' if is_hd else 'NEG'

    base_row = dict(DEFAULTS)
    base_row.update({
        'Age': age, 'Sex': 'M' if sex == 1 else 'F', 'Height': height, 'Weight': weight,
        'BMI': bmi,
        'Albumin_lab': albumin, 'Albumin': albumin,
        'WBC': f('WBC', 7.73),
        'Platelet': f('Platelet', 165.0),
        'AST': f('AST', 25),
        'ALT': f('ALT', 25),
        'hsCRP': f('hs_CRP', 1.0),
        'SerumCr': scr, 'CrCL_CG': crcl, 'BSA': bsa, 'eGFR': egfr,
        'age_group': age_group, 'is_HD': is_hd, 'remark_label': remark_label,
        'group': group,
    })
    return {
        'group': group, 'base_row': base_row,
        'derived': {'crcl_mL_min': crcl, 'bmi': bmi, 'bsa': bsa, 'egfr': egfr},
    }


def _predict_targets(group: str, row: dict, targets: list[str]) -> dict:
    import pandas as pd

    metrics = _load_metrics().get(group, {})
    out = {}
    for target in targets:
        try:
            pipe, features = _load_bundle(group, target)
        except FileNotFoundError as e:
            logger.warning(str(e))
            continue
        X = pd.DataFrame([{k: row.get(k) for k in features}])
        pred = float(pipe.predict(X)[0])
        m = metrics.get(target, {})
        out[target] = {'value': round(pred, 2), 'rmse': m.get('rmse'), 'mae': m.get('mae')}
    return out


def _landmark_curve(peaks: list[float], troughs: list[float], q_hr: float,
                     infusion_h: float = 1.0) -> list[dict]:
    """사이클별 Peak/Trough 랜드마크를 주입 상승(선형)+투여후 지수감쇠로 잇는다.

    Hybrid_model_2cm_bs_pipet/model/deep_learning/visualize_hybrid.py의
    표준 1-compartment 정상상태 근사를 사용한다 (임의 보간이 아님):
      - 제거속도상수 k_e = ln(Peak / Trough) / (다음 투여시각 − Peak 시각)
        → 모델이 예측한 그 사이클의 Peak/Trough 두 값 자체에서 역산.
      - 투여 후 감쇠: C(t) = Peak · exp(-k_e · (t − peak_t))       [1-comp 표준 감쇠식]
      - 주입 중 상승: C(t) = Peak − (Peak − prev_trough) · exp(-k_e · (t − dose_t))
        [zero-order infusion을 동일 k_e로 근사 — 분포용적/주입속도 미상이므로
         상승·감쇠에 같은 제거속도상수를 적용해 임의 선형보다 약동학적으로 타당하게 처리]
    """
    points = []
    prev_trough = 0.0
    dose_t = 0.0
    n = len(peaks)
    for i in range(n):
        peak = max(float(peaks[i]), 0.01)
        trough = max(float(troughs[i]), 0.01)
        if trough >= peak:
            trough = peak * 0.9  # 모델 예측이 역전된 경우 방어 (trough < peak 강제)
        peak_t = dose_t + infusion_h
        next_dose_t = dose_t + q_hr
        trough_t = next_dose_t

        # k_e: 이 사이클의 peak→trough 구간(주입 종료~다음 투여)에서 역산한 제거속도상수 (1/hr)
        import math
        k_e = math.log(peak / trough) / max(trough_t - peak_t, 1e-6)

        rise_steps = 8
        rise_t = [dose_t + (peak_t - dose_t) * k / (rise_steps - 1) for k in range(rise_steps)]
        rise_y = [peak - (peak - prev_trough) * math.exp(-k_e * (t - dose_t)) for t in rise_t]
        rise_y[-1] = peak

        decay_steps = 24
        decay_t = [peak_t + (trough_t - peak_t) * k / (decay_steps - 1) for k in range(decay_steps)]
        decay_y = [peak * math.exp(-k_e * (t - peak_t)) for t in decay_t]
        decay_y[-1] = trough

        n_rise = len(rise_t)
        for idx, (t, c) in enumerate(zip(rise_t, rise_y)):
            is_last = (idx == n_rise - 1)
            points.append({
                't_hr': round(t, 2), 'conc': round(c, 3),
                'is_dose': (idx == 0), 'is_tdm': is_last, 'is_peak': is_last,
            })
        for t, c in zip(decay_t[1:], decay_y[1:]):
            is_trough_pt = (t == trough_t)
            points.append({
                't_hr': round(t, 2), 'conc': round(c, 3),
                'is_dose': False, 'is_tdm': is_trough_pt, 'is_trough': is_trough_pt,
            })

        prev_trough = trough
        dose_t = next_dose_t
    return points


def predict_tdm_v2(patient: dict, cycle_seq: int = 1, dose_interval_hr: float | None = None,
                    doses_per_day: float | None = None,
                    blood_collection_hour: float | None = None,
                    hours_from_request_to_collection: float | None = None,
                    n_doses: int = 5) -> dict:
    """환자군 자동판정 + 5타겟(dose_mg/Peak/Trough/AUC/target_concentration) XGBoost 예측
    + 사이클별 Peak/Trough를 반복 예측해 재구성한 농도 곡선.

    patient: {age, sex(0/1), height, weight, is_hd(bool),
              Serum_Cr, CrCL?, Albumin, AST, ALT, WBC, Platelet, hs_CRP}
    cycle_seq: 대표 사이클(요약 KPI에 사용). 곡선은 1..n_doses 전체를 반복 예측해 구성.
    dose_interval_hr / doses_per_day: 투여 계획 (없으면 기본값)
    blood_collection_hour / hours_from_request_to_collection:
        target_concentration(채혈 시점 농도) 예측용 — 없으면 해당 타겟은 생략
    n_doses: 곡선에 사용할 사이클 수 (1~5)

    반환: {group, predictions, derived, curve: [{t_hr, conc, is_dose, is_tdm}], model_meta}
    """
    ctx = _build_patient_context(patient)
    group, base_row = ctx['group'], ctx['base_row']
    n_doses = max(1, min(5, int(n_doses)))
    q_hr = float(dose_interval_hr) if dose_interval_hr else 12.0

    # 대표 사이클 KPI (dose_mg/AUC/target_concentration 포함)
    rep_row = dict(base_row)
    rep_row.update({
        'CycleSequence': float(cycle_seq),
        'DoseIntervalHr': dose_interval_hr if dose_interval_hr else DEFAULTS.get('DoseIntervalHr'),
        'DosesPerDay': doses_per_day if doses_per_day else DEFAULTS['DosesPerDay'],
        'concentration_event_index': 1.0,
        'blood_collection_hour': blood_collection_hour,
        'hours_from_request_to_collection': hours_from_request_to_collection,
    })
    targets = list(TARGETS)
    if blood_collection_hour is None or hours_from_request_to_collection is None:
        targets.remove('target_concentration')
    predictions = _predict_targets(group, rep_row, targets)

    # 사이클별 Peak/Trough 반복 예측 → 곡선 재구성
    peaks, troughs = [], []
    for cyc in range(1, n_doses + 1):
        cyc_row = dict(base_row)
        cyc_row.update({
            'CycleSequence': float(cyc),
            'DoseIntervalHr': dose_interval_hr if dose_interval_hr else DEFAULTS.get('DoseIntervalHr'),
            'DosesPerDay': doses_per_day if doses_per_day else DEFAULTS['DosesPerDay'],
        })
        cyc_pred = _predict_targets(group, cyc_row, ['EstimatedPeak', 'EstimatedTrough'])
        peaks.append(cyc_pred.get('EstimatedPeak', {}).get('value', 0.0))
        troughs.append(cyc_pred.get('EstimatedTrough', {}).get('value', 0.0))

    curve = _landmark_curve(peaks, troughs, q_hr) if peaks else []

    return {
        'group': group,
        'predictions': predictions,
        'derived': ctx['derived'],
        'curve': curve,
        'cycle_peaks': [round(p, 2) for p in peaks],
        'cycle_troughs': [round(t, 2) for t in troughs],
        'model_meta': {'model': 'xgboost', 'group': group, 'n_doses': n_doses, 'q_hr': q_hr},
    }
