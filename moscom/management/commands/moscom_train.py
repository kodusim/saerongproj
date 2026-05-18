"""moscom Collection 데이터로 모기 발생 예측 모델 학습.

사용:
  python manage.py moscom_train
  python manage.py moscom_train --min-days 5  # 장비당 최소 일수
  python manage.py moscom_train --no-weather  # 기상 피처 빼고 학습

산출물:
  moscom/ml/best_model_RandomForest.joblib
  moscom/ml/feature_cols.joblib
  moscom/ml/training_report.json
"""
import os
import json
import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from collections import defaultdict

import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDate

logger = logging.getLogger(__name__)


ML_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ml')


class Command(BaseCommand):
    help = 'Collection 데이터로 모기 예측 모델 학습'

    def add_arguments(self, parser):
        parser.add_argument('--min-days', type=int, default=5, help='장비당 최소 데이터 일수 (기본 5)')
        parser.add_argument('--no-weather', action='store_true', help='기상 피처 제외')
        parser.add_argument('--test-size', type=float, default=0.2, help='holdout 비율')

    def handle(self, *args, **opts):
        os.makedirs(ML_DIR, exist_ok=True)
        from moscom.models import Device, Collection

        min_days = opts['min_days']
        use_weather = not opts['no_weather']
        test_size = opts['test_size']

        self.stdout.write(self.style.NOTICE('1) Collection → 장비×일 집계'))
        rows = list(
            Collection.objects
            .annotate(d=TruncDate('created_date'))
            .values('device_uuid', 'd')
            .annotate(total=Sum('mosquito_count'))
            .order_by('device_uuid', 'd')
        )
        self.stdout.write(f'   행 수: {len(rows)}')

        # 장비별 시계열로 정리
        dev_series = defaultdict(list)  # uuid -> [(date, total), ...]
        for r in rows:
            dev_series[r['device_uuid']].append((r['d'], r['total'] or 0))

        # 장비 메타
        devices = {d.device_uuid: d for d in Device.objects.all()}

        self.stdout.write(self.style.NOTICE('2) 피처 추출 (lag/MA/요일/권역/기상)'))
        records = []
        skipped_few = 0
        for uuid, series in dev_series.items():
            series.sort(key=lambda x: x[0])
            if len(series) < min_days:
                skipped_few += 1
                continue
            counts_by_date = {d: c for d, c in series}
            sorted_dates = [d for d, _ in series]

            dev_meta = devices.get(uuid)
            region_code = (dev_meta.region_code if dev_meta else '') or ''
            sido = (dev_meta.address_sido if dev_meta else '') or ''
            gungu = (dev_meta.address_gungu if dev_meta else '') or ''
            # 기상은 현재값 캐싱된 것만 있어 단일 — 모든 행에 동일 (target_date 정확한 매칭은 불가)
            temp = dev_meta.temperature if dev_meta else None
            humid = dev_meta.humidity if dev_meta else None
            precip = dev_meta.precipitation if dev_meta else None
            wind = dev_meta.wind_speed if dev_meta else None

            # 각 날짜에 대해 history 기반 lag 계산
            for i, (target_d, target_c) in enumerate(series):
                if i < 3:
                    # lag3 못 채우면 skip
                    continue
                # lag1, lag2, lag3, lag7
                def get_lag(k):
                    if i - k < 0:
                        return None
                    return series[i - k][1]
                lag1 = get_lag(1); lag2 = get_lag(2); lag3 = get_lag(3); lag7 = get_lag(7)
                if lag1 is None or lag2 is None or lag3 is None:
                    continue

                # MA3 (앞 3일 평균), MA7 (앞 7일 평균)
                prev_3 = [series[i-k][1] for k in (1, 2, 3)]
                ma3 = sum(prev_3) / 3
                prev_7 = [series[i-k][1] for k in range(1, min(8, i+1))]
                ma7 = sum(prev_7) / len(prev_7) if prev_7 else 0

                weekday = target_d.weekday()  # 0=Mon
                rec = {
                    'lag1': lag1, 'lag2': lag2, 'lag3': lag3,
                    'lag7': lag7 if lag7 is not None else ma7,  # lag7 없으면 ma7로 imputation
                    'ma3': ma3, 'ma7': ma7,
                    'weekday': weekday, 'is_weekend': 1 if weekday >= 5 else 0,
                    'month': target_d.month, 'day': target_d.day,
                    'region_code': region_code or 'NONE',
                    'sido': sido or 'NONE',
                    'target': target_c,
                }
                if use_weather:
                    rec['temperature'] = temp if temp is not None else 22.0
                    rec['humidity'] = humid if humid is not None else 60.0
                    rec['precipitation'] = precip if precip is not None else 0.0
                    rec['wind_speed'] = wind if wind is not None else 2.0
                records.append(rec)

        self.stdout.write(f'   학습 행: {len(records)}, 건너뛴 장비(데이터부족): {skipped_few}')
        if len(records) < 50:
            self.stdout.write(self.style.ERROR(f'데이터가 너무 적습니다 ({len(records)} 행). 학습 중단.'))
            return

        df = pd.DataFrame(records)

        # 모기지수 라벨 — 우리만의 다축 합성공식 (moscom/mosquito_index.py)
        from moscom.mosquito_index import (
            axis_count, axis_trend, axis_weather, axis_habitat,
            WEIGHTS as MI_WEIGHTS, compute_index,
        )
        p95 = float(np.percentile(df['target'].values, 95))
        if p95 <= 0:
            p95 = 100.0
        self.stdout.write(f'   P95(95분위 마릿수): {p95:.1f}  ← 마릿수정규화 기준')

        # 학습 행마다 그 시점의 4축 점수 + 종합 지수 부여
        target_index = []
        for r in records:
            # 7일 평균은 ma7 (이미 학습 피처에 들어있음)
            last7_avg = r.get('ma7', 0)
            # axis_trend 는 list 를 받으니 ma7 로 대체된 단일값을 7번 복제
            last7_proxy = [last7_avg] * 7
            mi = compute_index(
                count=r['target'],
                last7_counts=last7_proxy,
                temperature=r.get('temperature'),
                humidity=r.get('humidity'),
                p95=p95,
                name=r.get('region_code', '') or '',  # 권역 키로 habitat 추정 (정확하진 않음)
                addr='', detail='',
            )
            target_index.append(mi['index'])

        df['target_index'] = target_index

        # 카테고리 인코딩
        df_enc = pd.get_dummies(df, columns=['region_code', 'sido'], drop_first=False)
        # 마릿수 모델 타깃
        y_count = df_enc.pop('target').values
        # 모기지수 모델 타깃 (별도 변수)
        y_index = df_enc.pop('target_index').values
        X = df_enc.values.astype('float64')
        feature_cols = list(df_enc.columns)

        self.stdout.write(self.style.NOTICE(f'3) 학습 (피처 {len(feature_cols)}개)'))
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        # 마릿수 모델 + 모기지수 모델 — 동일 X, 다른 y. split도 동일하게.
        idx_tr, idx_te = train_test_split(np.arange(len(y_count)), test_size=test_size, random_state=42)
        X_tr, X_te = X[idx_tr], X[idx_te]
        y_tr, y_te = y_count[idx_tr], y_count[idx_te]
        y_idx_tr, y_idx_te = y_index[idx_tr], y_index[idx_te]

        model = RandomForestRegressor(
            n_estimators=200, max_depth=12, min_samples_leaf=2,
            n_jobs=-1, random_state=42,
        )
        model.fit(X_tr, y_tr)
        pred_tr = model.predict(X_tr)
        pred_te = model.predict(X_te)

        # 모기지수 모델
        model_idx = RandomForestRegressor(
            n_estimators=200, max_depth=12, min_samples_leaf=2,
            n_jobs=-1, random_state=42,
        )
        model_idx.fit(X_tr, y_idx_tr)
        pred_idx_tr = model_idx.predict(X_tr)
        pred_idx_te = model_idx.predict(X_te)

        report = {
            'n_samples': len(records),
            'n_features': len(feature_cols),
            'n_train': len(X_tr),
            'n_test': len(X_te),
            'p95_count': p95,
            'mi_weights': list(MI_WEIGHTS),
            # 마릿수 모델
            'count_train_mae': float(mean_absolute_error(y_tr, pred_tr)),
            'count_train_rmse': float(np.sqrt(mean_squared_error(y_tr, pred_tr))),
            'count_train_r2': float(r2_score(y_tr, pred_tr)),
            'count_test_mae': float(mean_absolute_error(y_te, pred_te)),
            'count_test_rmse': float(np.sqrt(mean_squared_error(y_te, pred_te))),
            'count_test_r2': float(r2_score(y_te, pred_te)),
            # 모기지수 모델
            'index_train_mae': float(mean_absolute_error(y_idx_tr, pred_idx_tr)),
            'index_train_r2': float(r2_score(y_idx_tr, pred_idx_tr)),
            'index_test_mae': float(mean_absolute_error(y_idx_te, pred_idx_te)),
            'index_test_r2': float(r2_score(y_idx_te, pred_idx_te)),
            'index_mean': float(np.mean(y_index)),
            'index_max': float(np.max(y_index)),
            # 호환용 (기존 키)
            'train_mae': float(mean_absolute_error(y_tr, pred_tr)),
            'train_rmse': float(np.sqrt(mean_squared_error(y_tr, pred_tr))),
            'train_r2': float(r2_score(y_tr, pred_tr)),
            'test_mae': float(mean_absolute_error(y_te, pred_te)),
            'test_rmse': float(np.sqrt(mean_squared_error(y_te, pred_te))),
            'test_r2': float(r2_score(y_te, pred_te)),
            'target_mean': float(np.mean(y_count)),
            'target_max': float(np.max(y_count)),
            'target_min': float(np.min(y_count)),
            'use_weather': use_weather,
            'trained_at': timezone.now().isoformat(),
            'feature_cols_preview': feature_cols[:25],
        }
        # 피처 중요도 상위 15개 (마릿수 모델 기준)
        try:
            imp = sorted(zip(feature_cols, model.feature_importances_), key=lambda x: -x[1])[:15]
            report['top_features'] = [{'name': n, 'importance': float(v)} for n, v in imp]
        except Exception:
            pass

        self.stdout.write(self.style.NOTICE('4) 평가 지표 — 마릿수 모델'))
        for k in ('count_train_mae', 'count_train_rmse', 'count_train_r2',
                  'count_test_mae', 'count_test_rmse', 'count_test_r2'):
            self.stdout.write(f'   {k:>20s}: {report[k]:.3f}')
        self.stdout.write(f'   target_mean: {report["target_mean"]:.2f}, max: {report["target_max"]}')
        self.stdout.write(self.style.NOTICE('   — 모기지수 모델'))
        for k in ('index_train_mae', 'index_train_r2', 'index_test_mae', 'index_test_r2'):
            self.stdout.write(f'   {k:>20s}: {report[k]:.3f}')
        self.stdout.write(f'   index_mean: {report["index_mean"]:.2f}, max: {report["index_max"]:.2f}')
        self.stdout.write('   top features (마릿수 모델 기준):')
        for f in (report.get('top_features') or [])[:10]:
            self.stdout.write(f'      {f["name"]:30s}  {f["importance"]:.3f}')

        # 저장
        import joblib
        model_path = os.path.join(ML_DIR, 'best_model_RandomForest.joblib')
        model_idx_path = os.path.join(ML_DIR, 'best_model_MosquitoIndex.joblib')
        feat_path = os.path.join(ML_DIR, 'feature_cols.joblib')
        meta_path = os.path.join(ML_DIR, 'training_meta.joblib')
        report_path = os.path.join(ML_DIR, 'training_report.json')
        joblib.dump(model, model_path)
        joblib.dump(model_idx, model_idx_path)
        joblib.dump(feature_cols, feat_path)
        joblib.dump({'p95': p95, 'mi_weights': list(MI_WEIGHTS)}, meta_path)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f'저장 완료: {model_path}'))
        self.stdout.write(self.style.SUCCESS(f'         : {model_idx_path}'))
        self.stdout.write(self.style.SUCCESS(f'         : {feat_path}'))
        self.stdout.write(self.style.SUCCESS(f'         : {meta_path}  (p95={p95:.1f})'))
        self.stdout.write(self.style.SUCCESS(f'         : {report_path}'))
