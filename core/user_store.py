"""
모기 대시보드용 간이 사용자 저장소.

스토리지: JSON 파일 (core/mosquito_users.json).
- admin은 하드코딩. 비밀번호 변경 안 됨. 모든 장비 접근 가능.
- 일반 사용자는 여기서 관리. {login_id: {password_hash, allowed_devices, created_at}}
- 비밀번호는 Django의 make_password/check_password 사용 (pbkdf2).
"""
import os
import json
import threading
from datetime import datetime

from django.contrib.auth.hashers import make_password, check_password

STORE_PATH = os.path.join(os.path.dirname(__file__), 'mosquito_users.json')
_LOCK = threading.RLock()

ADMIN_ID = 'admin'
ADMIN_PW = 'admin'


def _load():
    with _LOCK:
        if not os.path.exists(STORE_PATH):
            return {}
        try:
            with open(STORE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
        except (json.JSONDecodeError, OSError):
            return {}


def _save(data):
    with _LOCK:
        tmp = STORE_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STORE_PATH)


def list_users():
    """저장된 일반 사용자 목록 (admin 제외).
    [{login_id, allowed_devices, created_at, updated_at}, ...]
    """
    data = _load()
    out = []
    for uid, row in data.items():
        out.append({
            'login_id': uid,
            'allowed_devices': list(row.get('allowed_devices') or []),
            'created_at': row.get('created_at'),
            'updated_at': row.get('updated_at'),
        })
    out.sort(key=lambda x: x['login_id'])
    return out


def authenticate(login_id, password):
    """admin 또는 저장된 사용자 자격증명 확인.
    성공 시 {login_id, is_admin, allowed_devices}, 실패 시 None.
    """
    if login_id == ADMIN_ID and password == ADMIN_PW:
        return {'login_id': ADMIN_ID, 'is_admin': True, 'allowed_devices': None}  # None = 전체
    data = _load()
    row = data.get(login_id)
    if not row:
        return None
    if not check_password(password, row.get('password_hash', '')):
        return None
    return {
        'login_id': login_id,
        'is_admin': False,
        'allowed_devices': list(row.get('allowed_devices') or []),
    }


def create_user(login_id, password, allowed_devices):
    """새 사용자 생성. login_id 중복/admin 예약 시 ValueError."""
    login_id = (login_id or '').strip()
    if not login_id:
        raise ValueError('아이디를 입력하세요')
    if login_id == ADMIN_ID:
        raise ValueError('admin은 예약된 아이디입니다')
    if not password or len(password) < 3:
        raise ValueError('비밀번호는 3자 이상')
    data = _load()
    if login_id in data:
        raise ValueError('이미 존재하는 아이디입니다')
    now = datetime.utcnow().isoformat() + 'Z'
    data[login_id] = {
        'password_hash': make_password(password),
        'allowed_devices': list(allowed_devices or []),
        'created_at': now,
        'updated_at': now,
    }
    _save(data)
    return data[login_id]


def update_user(login_id, password=None, allowed_devices=None):
    """기존 사용자 수정. password는 지정 시만 변경. allowed_devices는 지정 시 교체."""
    if login_id == ADMIN_ID:
        raise ValueError('admin은 수정할 수 없습니다')
    data = _load()
    row = data.get(login_id)
    if not row:
        raise ValueError('존재하지 않는 사용자')
    if password is not None:
        if len(password) < 3:
            raise ValueError('비밀번호는 3자 이상')
        row['password_hash'] = make_password(password)
    if allowed_devices is not None:
        row['allowed_devices'] = list(allowed_devices)
    row['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    data[login_id] = row
    _save(data)
    return row


def delete_user(login_id):
    if login_id == ADMIN_ID:
        raise ValueError('admin은 삭제할 수 없습니다')
    data = _load()
    if login_id not in data:
        raise ValueError('존재하지 않는 사용자')
    del data[login_id]
    _save(data)
    return True


def is_device_allowed(session_user, device_uuid):
    """세션의 사용자가 해당 장비 접근 가능한지. admin은 전부 True."""
    if not session_user:
        return False
    if session_user.get('is_admin'):
        return True
    allowed = session_user.get('allowed_devices')
    if not allowed:
        return False
    return device_uuid in allowed


def filter_devices(session_user, devices):
    """장비 리스트에서 접근 가능한 것만 남김. admin은 그대로."""
    if not session_user or session_user.get('is_admin'):
        return list(devices or [])
    allowed = set(session_user.get('allowed_devices') or [])
    return [d for d in (devices or []) if (d.get('device_uuid') or d.get('uuid') or '') in allowed]


def allowed_uuid_set(session_user):
    """세션 사용자의 허용 장비 UUID 집합. admin은 None(=전체 허용)."""
    if session_user and session_user.get('is_admin'):
        return None
    return set((session_user or {}).get('allowed_devices') or [])
