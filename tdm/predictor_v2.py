"""TDM 예측 v2 — 환자군 4분류(Adult/AdultHD/Pediatric/PediatricHD) 별 XGBoost.

출처: OneDrive 농도예측3/only_Machine_model_patient (model_result/{group}/{target}_xgboost.joblib)
모델 파일: tdm/ml_artifacts_v2/{group}/{target}_xgboost.joblib (gitignore — 서버 별도 scp)

타겟 5종: dose_mg, EstimatedPeak, EstimatedTrough, AUC, target_concentration
joblib 번들 구조: {'pipeline': sklearn Pipeline, 'features': [...], 'target': str, 'model': str}

Lazy load + lru_cache. 첫 요청 때만 그룹×타겟 조합을 로드.
"""
from __future__ import annotations
import json
import logging
import os
import re
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


def predict_tdm_v2(patient: dict, cycle_seq: int = 1, dose_interval_hr: float | None = None,
                    doses_per_day: float | None = None,
                    blood_collection_hour: float | None = None,
                    hours_from_request_to_collection: float | None = None) -> dict:
    """환자군 자동판정 + 5타겟(dose_mg/Peak/Trough/AUC/target_concentration) XGBoost 예측.

    patient: {age, sex(0/1), height, weight, is_hd(bool),
              Serum_Cr, CrCL?, Albumin, AST, ALT, WBC, Platelet, hs_CRP}
    cycle_seq: TDM 사이클 순번 (CycleSequence)
    dose_interval_hr / doses_per_day: 투여 계획 (없으면 기본값)
    blood_collection_hour / hours_from_request_to_collection:
        target_concentration(채혈 시점 농도) 예측용 — 없으면 해당 타겟은 생략

    반환: {group, predictions: {target: {value, rmse, mae}}, derived: {...}}
    """
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

    row = dict(DEFAULTS)
    row.update({
        'Age': age, 'Sex': 'M' if sex == 1 else 'F', 'Height': height, 'Weight': weight,
        'BMI': bmi, 'CycleSequence': float(cycle_seq),
        'DoseIntervalHr': dose_interval_hr if dose_interval_hr else DEFAULTS.get('DoseIntervalHr'),
        'DosesPerDay': doses_per_day if doses_per_day else DEFAULTS['DosesPerDay'],
        'Albumin_lab': albumin, 'Albumin': albumin,
        'WBC': f('WBC', 7.73),
        'Platelet': f('Platelet', 165.0),
        'AST': f('AST', 25),
        'ALT': f('ALT', 25),
        'hsCRP': f('hs_CRP', 1.0),
        'SerumCr': scr, 'CrCL_CG': crcl, 'BSA': bsa, 'eGFR': egfr,
        'age_group': age_group, 'is_HD': is_hd, 'remark_label': remark_label,
        'group': group,
        'concentration_event_index': 1.0,
        'blood_collection_hour': blood_collection_hour,
        'hours_from_request_to_collection': hours_from_request_to_collection,
    })

    import pandas as pd

    metrics = _load_metrics().get(group, {})
    predictions = {}
    targets = list(TARGETS)
    if blood_collection_hour is None or hours_from_request_to_collection is None:
        targets.remove('target_concentration')

    for target in targets:
        try:
            pipe, features = _load_bundle(group, target)
        except FileNotFoundError as e:
            logger.warning(str(e))
            continue
        X = pd.DataFrame([{k: row.get(k) for k in features}])
        pred = float(pipe.predict(X)[0])
        m = metrics.get(target, {})
        predictions[target] = {
            'value': round(pred, 2),
            'rmse': m.get('rmse'),
            'mae': m.get('mae'),
        }

    return {
        'group': group,
        'predictions': predictions,
        'derived': {
            'crcl_mL_min': crcl, 'bmi': bmi, 'bsa': bsa, 'egfr': egfr,
        },
        'model_meta': {'model': 'xgboost', 'group': group},
    }
