"""
방역 계획 저장소 + 효과 계산 모듈.

스토리지: JSON 파일 (core/remedy_plans.json).
각 계획:
  {
    id: "r_xxxxx",
    owner_id: "login_id",     # 생성한 사용자
    device_uuid: str,          # 어느 장비(관측소)
    method_key: str,           # METHODS 키
    scheduled_date: "YYYY-MM-DD",   # 방역 실시 예정일 (KST)
    note: str,
    created_at, updated_at
  }

효과 반영: 예측 날짜 D에 대해, scheduled_date..scheduled_date+duration 사이면
  predicted_count *= (1 - reduction_pct/100)
여러 방역이 중첩되면 곱셈 누적.
"""
import os
import json
import uuid
import threading
from datetime import datetime, date, timedelta

STORE_PATH = os.path.join(os.path.dirname(__file__), 'remedy_plans.json')
_LOCK = threading.RLock()


# 방역 방법 6종 (사용자 지시 + 문헌 기반)
METHODS = {
    'bti_larvicide': {
        'key': 'bti_larvicide',
        'name': 'BTi 유충 방제 (생물학적)',
        'target': '유충',
        'onset_days': 1,          # 효과 시작 (방역일 + N일)
        'duration_days': 10,      # 지속
        'reduction_pct': 65,      # 감소율 %
        'note': '생물학적 제제. 수질 영향 적음.',
    },
    'igr_growth_regulator': {
        'key': 'igr_growth_regulator',
        'name': 'IGR 유충 성장 억제제',
        'target': '유충',
        'onset_days': 2,
        'duration_days': 17,
        'reduction_pct': 55,
        'note': '유충→성충 전환 차단. 장기 지속.',
    },
    'ulv_fog': {
        'key': 'ulv_fog',
        'name': 'ULV 초미립자 연막 (피레스로이드)',
        'target': '성충',
        'onset_days': 0,
        'duration_days': 3,
        'reduction_pct': 78,
        'note': '즉시 효과, 단기. 야간 실시 권장.',
    },
    'residual_spray': {
        'key': 'residual_spray',
        'name': '잔류 분무 (벽면 방제)',
        'target': '성충',
        'onset_days': 0,
        'duration_days': 45,
        'reduction_pct': 55,
        'note': '외벽·처마에 분무. 지속 기간 길다.',
    },
    'habitat_removal': {
        'key': 'habitat_removal',
        'name': '서식지 제거 (물웅덩이/배수)',
        'target': '서식지',
        'onset_days': 3,
        'duration_days': 60,
        'reduction_pct': 85,
        'note': '근본 해결. 장기 효과.',
    },
    'smart_trap': {
        'key': 'smart_trap',
        'name': '스마트 트랩 설치',
        'target': '성충',
        'onset_days': 0,
        'duration_days': 365,
        'reduction_pct': 25,
        'note': '보조 수단. 감소율은 낮지만 상시 작동.',
    },
}


def list_methods():
    return list(METHODS.values())


# ── storage ─────────────────────────────────────────────

def _load():
    with _LOCK:
        if not os.path.exists(STORE_PATH):
            return []
        try:
            with open(STORE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f) or []
        except (json.JSONDecodeError, OSError):
            return []


def _save(data):
    with _LOCK:
        tmp = STORE_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STORE_PATH)


def list_plans(visible_uuids=None):
    """visible_uuids=None: 전체. 집합이면 해당 장비 계획만 반환."""
    plans = _load()
    if visible_uuids is not None:
        plans = [p for p in plans if p.get('device_uuid') in visible_uuids]
    # 최신 스케줄 먼저
    plans.sort(key=lambda p: (p.get('scheduled_date') or '', p.get('created_at') or ''), reverse=True)
    return plans


def get_plan(plan_id):
    for p in _load():
        if p.get('id') == plan_id:
            return p
    return None


def _validate(plan, require_all=True):
    errs = []
    if require_all or 'device_uuid' in plan:
        if not plan.get('device_uuid'):
            errs.append('장비를 선택하세요')
    if require_all or 'method_key' in plan:
        mk = plan.get('method_key')
        if mk not in METHODS:
            errs.append('방역 방법 선택이 올바르지 않습니다')
    if require_all or 'scheduled_date' in plan:
        sd = plan.get('scheduled_date') or ''
        try:
            datetime.strptime(sd, '%Y-%m-%d')
        except ValueError:
            errs.append('예정일 형식은 YYYY-MM-DD')
    if errs:
        raise ValueError(' / '.join(errs))


def create_plan(owner_id, device_uuid, method_key, scheduled_date, note=''):
    now = datetime.utcnow().isoformat() + 'Z'
    plan = {
        'id': 'r_' + uuid.uuid4().hex[:10],
        'owner_id': owner_id,
        'device_uuid': device_uuid,
        'method_key': method_key,
        'scheduled_date': scheduled_date,
        'note': (note or '').strip()[:200],
        'created_at': now,
        'updated_at': now,
    }
    _validate(plan)
    data = _load()
    data.append(plan)
    _save(data)
    return plan


def update_plan(plan_id, patch):
    data = _load()
    for p in data:
        if p.get('id') == plan_id:
            merged = {**p, **{k: v for k, v in patch.items() if k in ('device_uuid','method_key','scheduled_date','note')}}
            _validate(merged, require_all=False)
            merged['note'] = (merged.get('note') or '').strip()[:200]
            merged['updated_at'] = datetime.utcnow().isoformat() + 'Z'
            p.update(merged)
            _save(data)
            return p
    raise ValueError('해당 계획을 찾을 수 없습니다')


def delete_plan(plan_id):
    data = _load()
    new_data = [p for p in data if p.get('id') != plan_id]
    if len(new_data) == len(data):
        raise ValueError('해당 계획을 찾을 수 없습니다')
    _save(new_data)
    return True


# ── 효과 계산 ────────────────────────────────────────────

def _parse_date(s):
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except Exception:
        return None


def adjustment_factor(device_uuid, target_date):
    """device_uuid의 target_date 예측값에 곱할 감소 계수(0~1).
    여러 방역이 겹치면 곱셈 누적. 방역 없으면 1.0.

    target_date: datetime.date 또는 'YYYY-MM-DD'
    """
    if isinstance(target_date, str):
        td = _parse_date(target_date)
    else:
        td = target_date
    if not td:
        return 1.0, []

    factor = 1.0
    applied = []
    for p in _load():
        if p.get('device_uuid') != device_uuid:
            continue
        sched = _parse_date(p.get('scheduled_date'))
        if not sched:
            continue
        method = METHODS.get(p.get('method_key'))
        if not method:
            continue
        start = sched + timedelta(days=method['onset_days'])
        end = start + timedelta(days=method['duration_days'])
        if start <= td <= end:
            factor *= (1 - method['reduction_pct'] / 100.0)
            applied.append({
                'plan_id': p['id'],
                'method_key': method['key'],
                'method_name': method['name'],
                'scheduled_date': p['scheduled_date'],
                'reduction_pct': method['reduction_pct'],
            })
    return factor, applied


def adjust_predictions(predictions_by_uuid):
    """예측 결과(dict: uuid → [{date, predicted}, ...])를 받아
    방역 효과 반영한 dict를 반환. 원본 수정하지 않음.
    반환: {uuid: {'predictions':[...], 'applied_by_date': {date:[{method_name,...}]}}}
    """
    out = {}
    for uuid_, preds in predictions_by_uuid.items():
        new_preds = []
        applied_by_date = {}
        for pp in preds:
            f, applied = adjustment_factor(uuid_, pp.get('date'))
            orig = pp.get('predicted', 0) or 0
            adj = int(round(orig * f))
            new_preds.append({
                'date': pp.get('date'),
                'predicted_raw': orig,
                'predicted': adj,
                'remedy_factor': round(f, 3),
            })
            if applied:
                applied_by_date[pp.get('date')] = applied
        out[uuid_] = {'predictions': new_preds, 'applied_by_date': applied_by_date}
    return out
