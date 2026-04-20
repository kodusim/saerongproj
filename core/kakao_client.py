"""
카카오톡 메시지 API 클라이언트.

- 로그인 URL 생성 (Authorization Code)
- 토큰 교환 (code → access_token, refresh_token)
- 토큰은 JSON 파일(core/kakao_tokens.json)에 저장. (로그인 사용자별)
- access_token 만료 시 refresh_token으로 자동 갱신
- /memo/default/send: 나에게 보내기 (기본 템플릿)
- /friends/message/default/send: 친구에게 보내기 (심사 필요)

File layout (kakao_tokens.json):
{
  "<session login_id>": {
    "access_token": "...",
    "refresh_token": "...",
    "access_expires_at": "2026-04-20T05:00:00Z",
    "refresh_expires_at": "2026-06-20T05:00:00Z",
    "connected_at": "...",
    "scopes": ["talk_message", ...]
  }
}
"""
import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

STORE_PATH = os.path.join(os.path.dirname(__file__), 'kakao_tokens.json')
_LOCK = threading.RLock()

AUTH_URL = 'https://kauth.kakao.com/oauth/authorize'
TOKEN_URL = 'https://kauth.kakao.com/oauth/token'
API_BASE = 'https://kapi.kakao.com'


# ─ 저장소 ──────────────────────────────────────────────────

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


def get_token(login_id):
    return _load().get(login_id)


def delete_token(login_id):
    data = _load()
    if login_id in data:
        del data[login_id]
        _save(data)
        return True
    return False


# ─ OAuth ──────────────────────────────────────────────────

def authorize_url(state=None, scope='talk_message'):
    """사용자를 카카오 로그인으로 보낼 URL"""
    params = {
        'client_id': settings.KAKAO_REST_API_KEY,
        'redirect_uri': settings.KAKAO_REDIRECT_URI,
        'response_type': 'code',
        'scope': scope,
    }
    if state:
        params['state'] = state
    return AUTH_URL + '?' + urlencode(params)


def exchange_code(code):
    """authorization code → 토큰 교환"""
    resp = requests.post(TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'client_id': settings.KAKAO_REST_API_KEY,
        'redirect_uri': settings.KAKAO_REDIRECT_URI,
        'code': code,
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()


def save_tokens_for(login_id, payload):
    """카카오 토큰 응답을 저장. payload는 exchange_code 결과."""
    now = datetime.now(timezone.utc)
    data = _load()
    entry = data.get(login_id) or {}
    entry['access_token'] = payload['access_token']
    if payload.get('refresh_token'):
        entry['refresh_token'] = payload['refresh_token']
    entry['access_expires_at'] = (now + timedelta(seconds=payload.get('expires_in', 0))).isoformat()
    if payload.get('refresh_token_expires_in'):
        entry['refresh_expires_at'] = (now + timedelta(seconds=payload['refresh_token_expires_in'])).isoformat()
    entry['scopes'] = (payload.get('scope') or '').split(' ')
    if 'connected_at' not in entry:
        entry['connected_at'] = now.isoformat()
    entry['updated_at'] = now.isoformat()
    data[login_id] = entry
    _save(data)
    return entry


def refresh_if_needed(login_id):
    """access_token 만료됐거나 5분 이내 만료면 refresh 시도."""
    entry = _load().get(login_id)
    if not entry or not entry.get('refresh_token'):
        return None
    now = datetime.now(timezone.utc)
    exp = entry.get('access_expires_at')
    try:
        exp_dt = datetime.fromisoformat(exp.replace('Z', '+00:00')) if exp else None
    except Exception:
        exp_dt = None
    if exp_dt and (exp_dt - now).total_seconds() > 300:
        return entry  # 아직 충분히 유효
    try:
        resp = requests.post(TOKEN_URL, data={
            'grant_type': 'refresh_token',
            'client_id': settings.KAKAO_REST_API_KEY,
            'refresh_token': entry['refresh_token'],
        }, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        # refresh_token 은 응답에 없을 수 있음 (기존 유지)
        return save_tokens_for(login_id, payload)
    except Exception as e:
        logger.exception('kakao refresh failed')
        return None


# ─ 메시지 전송 ──────────────────────────────────────────────

def _default_memo_template(text, link_url):
    return {
        'object_type': 'text',
        'text': text[:400],  # 최대 400자
        'link': {'web_url': link_url, 'mobile_web_url': link_url},
        'button_title': '대시보드 열기',
    }


def send_to_me(login_id, text, link_url=None):
    """나에게 보내기.
    Returns (ok, detail)
    """
    entry = refresh_if_needed(login_id)
    if not entry:
        return False, '카카오 연동이 필요합니다. 먼저 연결해주세요.'
    link = link_url or 'https://saerong.com/mosquito-test/'
    template = _default_memo_template(text, link)
    try:
        resp = requests.post(
            f'{API_BASE}/v2/api/talk/memo/default/send',
            headers={'Authorization': f'Bearer {entry["access_token"]}'},
            data={'template_object': json.dumps(template, ensure_ascii=False)},
            timeout=15,
        )
        if resp.status_code == 401:
            # 토큰 만료 → 강제 재발급 후 재시도
            refreshed = refresh_if_needed(login_id)
            if refreshed:
                resp = requests.post(
                    f'{API_BASE}/v2/api/talk/memo/default/send',
                    headers={'Authorization': f'Bearer {refreshed["access_token"]}'},
                    data={'template_object': json.dumps(template, ensure_ascii=False)},
                    timeout=15,
                )
        if resp.status_code >= 400:
            return False, f'카카오 오류 {resp.status_code}: {resp.text[:200]}'
        return True, resp.json()
    except Exception as e:
        logger.exception('kakao send_to_me failed')
        return False, f'요청 실패: {e}'
