"""Hybrid Vancomycin TDM 예측기 (ML + DL 2단계 추론).

특허: 농도예측_특허 / Hybrid_model_2cm_bs_pipet
- 1단계 ML: 환자 17개 covariate → ns_peak/trough 1~5 (10 targets)
- 2단계 DL (LSTM/RNN/Transformer): event sequence + ML prediction → 시간별 농도 곡선

Lazy load. 서버 시작 시 메모리 잡지 않고 첫 요청 때 1회 로드.
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

ART_DIR = os.path.join(os.path.dirname(__file__), 'ml_artifacts')

# ML 17 covariate (학습 시 순서와 동일)
ML_FEATURES = [
    'age', 'sex_id', 'height', 'weight', 'BMI', 'diagnosis_id',
    'CrCL_mL_per_min', 'Serum_Cr', 'Albumin', 'AST', 'ALT',
    'WBC', 'Platelet', 'hs_CRP',
    'initial_dose_mg', 'initial_q_hr', 'initial_daily_dose_mg',
]
ML_TARGETS = (
    [f'ns_peak_{i}' for i in range(1, 6)] +
    [f'ns_trough_{i}' for i in range(1, 6)]
)

# DL event-level features (학습 시 순서와 동일)
DL_BASE_FEATURES = [
    'age', 'sex_id', 'height', 'weight', 'BMI', 'diagnosis_id',
    'CrCL_mL_per_min', 'Serum_Cr', 'Albumin', 'AST', 'ALT',
    'WBC', 'Platelet', 'hs_CRP',
    'delta_hours', 'hours_since_cycle_start', 'hours_since_last_dose',
    'dose_mg', 'q_hr', 'is_tdm', 'is_dose',
]
DL_NS_PRED_COLS = [f'pred_{t}' for t in ML_TARGETS]
DL_LAST_NS_COLS = ['pred_last_ns_peak', 'pred_last_ns_trough', 'pred_last_ns_gap']
DL_FEATURES = DL_BASE_FEATURES + DL_NS_PRED_COLS + DL_LAST_NS_COLS  # 34개


@lru_cache(maxsize=1)
def _load_ml():
    """sklearn ExtraTrees joblib 로드. extra_trees → random_forest 폴백.

    joblib 파일 구조: {'model': Pipeline, 'feature_cols': list, 'target_cols': list, 'args': dict}
    """
    import joblib
    candidates = ['extra_trees.joblib', 'random_forest.joblib']
    for fname in candidates:
        path = os.path.join(ART_DIR, fname)
        if os.path.exists(path):
            logger.info('TDM ML 모델 로드: %s', fname)
            bundle = joblib.load(path)
            if isinstance(bundle, dict) and 'model' in bundle:
                return bundle['model'], bundle.get('feature_cols') or ML_FEATURES, bundle.get('target_cols') or ML_TARGETS, fname.replace('.joblib', '')
            # 구조가 다르면 raw sklearn 모델로 간주
            return bundle, ML_FEATURES, ML_TARGETS, fname.replace('.joblib', '')
    raise FileNotFoundError('TDM ML 모델 파일이 없습니다 (tdm/ml_artifacts/*.joblib)')


@lru_cache(maxsize=1)
def _load_dl():
    """PyTorch LSTM 가중치 로드. 없으면 None 반환 (DL 단계 건너뜀)."""
    pt_path = os.path.join(ART_DIR, 'best_lstm_ml-extra_trees.pt')
    if not os.path.exists(pt_path):
        logger.warning('TDM DL 모델 파일이 없습니다 (LSTM 단계 비활성)')
        return None, None, None
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
    except ImportError:
        logger.warning('PyTorch 미설치 — DL 단계 비활성')
        return None, None, None

    class HybridDLModel(nn.Module):
        def __init__(self, input_dim, hidden_size=64):
            super().__init__()
            self.input_norm = nn.LayerNorm(input_dim)
            self.backbone = nn.LSTM(input_dim, hidden_size, batch_first=True)
            self.hidden_norm = nn.LayerNorm(hidden_size)
            self.conc_head = nn.Sequential(
                nn.Linear(hidden_size, hidden_size), nn.ReLU(),
                nn.Linear(hidden_size, 1),
            )
            self.endpoint_head = nn.Sequential(
                nn.Linear(hidden_size, hidden_size), nn.ReLU(),
                nn.Linear(hidden_size, 3),
            )

        def forward(self, x, pad_mask):
            x = self.input_norm(x)
            h_seq, _ = self.backbone(x)
            h_seq = self.hidden_norm(h_seq)
            conc = F.softplus(self.conc_head(h_seq).squeeze(-1))
            lengths = pad_mask.sum(dim=1).long().clamp(min=1) - 1
            last_h = h_seq[torch.arange(h_seq.shape[0]), lengths]
            endpoint = F.softplus(self.endpoint_head(last_h))
            return conc, endpoint

    state = torch.load(pt_path, map_location='cpu', weights_only=False)
    sd = state.get('state_dict') if isinstance(state, dict) else state
    stats = state.get('stats') if isinstance(state, dict) else None
    feature_cols = state.get('feature_cols') if isinstance(state, dict) else None
    input_dim = state.get('input_dim') if isinstance(state, dict) else len(DL_FEATURES)
    model = HybridDLModel(input_dim=input_dim, hidden_size=64)
    model.load_state_dict(sd, strict=False)
    model.eval()
    logger.info('TDM DL 모델(LSTM) 로드 완료 (input_dim=%d)', input_dim)
    return model, stats, feature_cols or DL_FEATURES


def _calc_bmi(weight_kg, height_cm):
    if not weight_kg or not height_cm:
        return None
    h_m = height_cm / 100.0
    return round(weight_kg / (h_m * h_m), 2)


def _crcl_cockcroft_gault(age, sex, weight_kg, scr_mgdl):
    """Cockcroft-Gault CrCL (mL/min). sex: 1=남성, 0=여성."""
    if not all([age, weight_kg, scr_mgdl]) or scr_mgdl <= 0:
        return None
    crcl = ((140 - age) * weight_kg) / (72 * scr_mgdl)
    if sex == 0:
        crcl *= 0.85
    return round(crcl, 1)


def predict_tdm(patient: dict, dose_mg: float, q_hr: float, n_doses: int = 5,
                model_choice: str = 'auto', dose_dur_hr: float = 1.0) -> dict:
    """하이브리드 예측 실행.

    patient: {age, sex (0/1), height, weight, diagnosis_id, Serum_Cr, Albumin,
              AST, ALT, WBC, Platelet, hs_CRP, CrCL_mL_per_min?} — CrCL 빠지면 CG 자동 계산
    dose_mg: 1회 투여량 (mg)
    q_hr: 투여 간격 (hr)
    n_doses: 평가 사이클 수 (1~5)
    dose_dur_hr: 1회 infusion 길이 (기본 1시간)

    반환: {
      ml_predictions: {ns_peak_1..5, ns_trough_1..5},
      dl_curve: [{t_hr, conc}],            # 시간별 농도 곡선
      dl_endpoint: {steady_peak, steady_trough, steady_auc24},
      summary: {target_trough_ok, mic_warning, ...},
      model_meta: {ml_model, dl_model}
    }
    """
    import numpy as np

    # 1) 환자 기본 처리
    age = float(patient.get('age', 0))
    sex_id = int(patient.get('sex', 1))   # 1=남, 0=여
    height = float(patient.get('height', 170))
    weight = float(patient.get('weight', 65))
    bmi = _calc_bmi(weight, height)
    diagnosis_id = int(patient.get('diagnosis_id', 0))
    scr = float(patient.get('Serum_Cr', 1.0))
    crcl = patient.get('CrCL_mL_per_min')
    if crcl is None or crcl <= 0:
        crcl = _crcl_cockcroft_gault(age, sex_id, weight, scr) or 60.0
    crcl = float(crcl)

    daily_dose = dose_mg * (24.0 / q_hr) if q_hr > 0 else dose_mg

    ml_row = {
        'age': age, 'sex_id': sex_id, 'height': height, 'weight': weight,
        'BMI': bmi or 24.0, 'diagnosis_id': diagnosis_id,
        'CrCL_mL_per_min': crcl, 'Serum_Cr': scr,
        'Albumin': float(patient.get('Albumin', 3.5)),
        'AST': float(patient.get('AST', 25)),
        'ALT': float(patient.get('ALT', 25)),
        'WBC': float(patient.get('WBC', 7.0)),
        'Platelet': float(patient.get('Platelet', 200)),
        'hs_CRP': float(patient.get('hs_CRP', 1.0)),
        'initial_dose_mg': dose_mg, 'initial_q_hr': q_hr,
        'initial_daily_dose_mg': daily_dose,
    }

    # 2) ML 1단계 — 17 covariate → 10 NS targets
    ml_model, ml_feat_cols, ml_targ_cols, ml_name = _load_ml()
    X_ml = np.array([[ml_row.get(k, 0.0) for k in ml_feat_cols]], dtype=np.float64)
    ml_out = ml_model.predict(X_ml)[0]
    ml_predictions = {t: float(round(v, 2)) for t, v in zip(ml_targ_cols, ml_out)}

    # 3) Event sequence 구성 (1회당 dose + 24시간 후 trough 측정 가정)
    #    cycle = n_doses 회 투여 + 마지막 trough 측정 1점
    events = []
    t = 0.0
    last_dose_t = 0.0
    for i in range(1, n_doses + 1):
        events.append({
            'time': t, 'is_dose': 1, 'is_tdm': 0,
            'dose_mg': dose_mg, 'q_hr': q_hr,
            'hours_since_last_dose': 0.0 if i == 1 else q_hr,
            'delta_hours': 0.0 if i == 1 else q_hr,
        })
        last_dose_t = t
        # peak 측정 (dose 종료 후 30분)
        peak_t = t + dose_dur_hr + 0.5
        events.append({
            'time': peak_t, 'is_dose': 0, 'is_tdm': 1,
            'dose_mg': 0.0, 'q_hr': q_hr,
            'hours_since_last_dose': peak_t - last_dose_t,
            'delta_hours': dose_dur_hr + 0.5,
        })
        # trough 측정 (다음 dose 직전)
        trough_t = t + q_hr - 0.5
        events.append({
            'time': trough_t, 'is_dose': 0, 'is_tdm': 1,
            'dose_mg': 0.0, 'q_hr': q_hr,
            'hours_since_last_dose': trough_t - last_dose_t,
            'delta_hours': (q_hr - 0.5) - (dose_dur_hr + 0.5),
        })
        t += q_hr

    # 누적 hours_since_cycle_start
    for ev in events:
        ev['hours_since_cycle_start'] = ev['time']

    # 4) DL 2단계 (있으면)
    dl_model, dl_stats, dl_feat_cols = _load_dl()
    dl_curve = []
    dl_endpoint = None

    if dl_model is not None:
        try:
            import torch
            import numpy as np

            # 마지막 NS pred (5번째 사이클)
            last_peak = ml_predictions.get('ns_peak_5', 0.0)
            last_trough = ml_predictions.get('ns_trough_5', 0.0)
            last_gap = max(0.0, last_peak - last_trough)

            x_rows = []
            for ev in events:
                base = {
                    'age': age, 'sex_id': sex_id, 'height': height,
                    'weight': weight, 'BMI': bmi or 24.0,
                    'diagnosis_id': diagnosis_id, 'CrCL_mL_per_min': crcl,
                    'Serum_Cr': scr, 'Albumin': ml_row['Albumin'],
                    'AST': ml_row['AST'], 'ALT': ml_row['ALT'],
                    'WBC': ml_row['WBC'], 'Platelet': ml_row['Platelet'],
                    'hs_CRP': ml_row['hs_CRP'],
                    'delta_hours': ev['delta_hours'],
                    'hours_since_cycle_start': ev['hours_since_cycle_start'],
                    'hours_since_last_dose': ev['hours_since_last_dose'],
                    'dose_mg': ev['dose_mg'], 'q_hr': q_hr,
                    'is_tdm': ev['is_tdm'], 'is_dose': ev['is_dose'],
                }
                for k, v in ml_predictions.items():
                    base[f'pred_{k}'] = v
                base['pred_last_ns_peak'] = last_peak
                base['pred_last_ns_trough'] = last_trough
                base['pred_last_ns_gap'] = last_gap
                x_rows.append([float(base.get(k, 0.0)) for k in dl_feat_cols])

            X = np.array([x_rows], dtype=np.float32)   # (1, L, F)

            # 정규화 (학습 시 stats가 .pt에 있으면 사용)
            if dl_stats and isinstance(dl_stats, dict) and 'mean' in dl_stats and 'std' in dl_stats:
                mean = np.array([float(dl_stats['mean'].get(k, 0.0)) for k in dl_feat_cols], dtype=np.float32)
                std_raw = [dl_stats['std'].get(k, 1.0) for k in dl_feat_cols]
                std = np.array([float(s if s else 1.0) for s in std_raw], dtype=np.float32)
                X = (X - mean) / std

            pad_mask = torch.ones((1, len(events)), dtype=torch.float32)
            with torch.no_grad():
                conc, endpoint = dl_model(torch.from_numpy(X), pad_mask)
            conc_arr = conc.squeeze(0).cpu().numpy()
            ep_arr = endpoint.squeeze(0).cpu().numpy()

            for ev, c in zip(events, conc_arr):
                dl_curve.append({
                    't_hr': round(ev['time'], 2),
                    'conc': round(float(c), 3),
                    'is_dose': bool(ev['is_dose']),
                    'is_tdm': bool(ev['is_tdm']),
                })
            dl_endpoint = {
                'steady_peak': round(float(ep_arr[0]), 2),
                'steady_trough': round(float(ep_arr[1]), 2),
                'steady_auc24': round(float(ep_arr[2]), 1),
            }
        except Exception as e:
            logger.exception('DL inference failed: %s', e)

    # 5) Summary
    target_trough_lo, target_trough_hi = 15.0, 20.0     # MRSA 표적 (예시)
    target_auc_lo, target_auc_hi = 400.0, 600.0
    summary = {
        'derived_crcl': crcl,
        'derived_bmi': bmi,
        'daily_dose_mg': daily_dose,
        'target_trough_range_mg_L': [target_trough_lo, target_trough_hi],
        'target_auc24_range': [target_auc_lo, target_auc_hi],
    }
    if dl_endpoint:
        tr = dl_endpoint['steady_trough']
        summary['trough_status'] = (
            '저농도(증량 검토)' if tr < target_trough_lo else
            '과량(감량 검토)' if tr > target_trough_hi else
            '치료 영역'
        )
        au = dl_endpoint['steady_auc24']
        summary['auc_status'] = (
            '저AUC' if au < target_auc_lo else
            '고AUC(신독성 위험)' if au > target_auc_hi else
            '치료 영역'
        )
    else:
        # ML only fallback
        tr = ml_predictions.get('ns_trough_5', 0.0)
        summary['trough_status'] = (
            '저농도(증량 검토)' if tr < target_trough_lo else
            '과량(감량 검토)' if tr > target_trough_hi else
            '치료 영역'
        )

    return {
        'ml_predictions': ml_predictions,
        'dl_curve': dl_curve,
        'dl_endpoint': dl_endpoint,
        'summary': summary,
        'model_meta': {
            'ml_model': ml_name,
            'dl_model': 'lstm' if dl_model is not None else None,
            'n_doses': n_doses, 'q_hr': q_hr,
        },
    }
