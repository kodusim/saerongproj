"""
MOSCOM API 클라이언트

https://api.moscom.co.kr 에 접속해서 장비 데이터를 가져온다.
- 로그인: GET /account/login?loginId=X&password=Y (JWT 반환)
- 장비 목록: GET /device/listAll (Authorization: Bearer <JWT>)

토큰은 메모리에 캐싱하고, 401 발생 시 자동 재로그인한다.
장비 목록은 Redis에 60초간 캐싱해서 외부 API 부하를 줄인다.
"""
import os
import time
import logging
import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

API_BASE = os.environ.get('MOSCOM_API_BASE', 'https://api.moscom.co.kr')
LOGIN_ID = os.environ.get('MOSCOM_LOGIN_ID', 'admin')
LOGIN_PASSWORD = os.environ.get('MOSCOM_LOGIN_PASSWORD', 'admin')

TOKEN_CACHE_KEY = 'moscom:jwt'
DEVICES_CACHE_KEY = 'moscom:devices'
TOKEN_TTL = 23 * 60 * 60  # JWT는 24시간 유효, 23시간 캐싱
DEVICES_TTL = 60  # 장비 데이터는 60초 캐싱


class MoscomAPIError(Exception):
    pass


def _login():
    """MOSCOM 로그인, JWT 반환"""
    url = f'{API_BASE}/account/login'
    resp = requests.get(url, params={'loginId': LOGIN_ID, 'password': LOGIN_PASSWORD}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    token = data.get('token')
    if not token:
        raise MoscomAPIError(f'No token in login response: {data}')
    cache.set(TOKEN_CACHE_KEY, token, TOKEN_TTL)
    logger.info('MOSCOM login success')
    return token


def _get_token():
    """캐시된 JWT 반환, 없으면 로그인"""
    token = cache.get(TOKEN_CACHE_KEY)
    if not token:
        token = _login()
    return token


def _request(method, path, **kwargs):
    """인증이 필요한 API 호출, 401 시 자동 재로그인 후 재시도"""
    token = _get_token()
    headers = kwargs.pop('headers', {})
    headers['Authorization'] = f'Bearer {token}'
    headers.setdefault('Origin', 'https://moscom.co.kr')

    url = f'{API_BASE}{path}'
    resp = requests.request(method, url, headers=headers, timeout=15, **kwargs)

    if resp.status_code == 401:
        cache.delete(TOKEN_CACHE_KEY)
        token = _login()
        headers['Authorization'] = f'Bearer {token}'
        resp = requests.request(method, url, headers=headers, timeout=15, **kwargs)

    resp.raise_for_status()
    return resp.json()


def list_devices(force_refresh=False):
    """전체 장비 목록 조회 (60초 캐싱)"""
    if not force_refresh:
        cached = cache.get(DEVICES_CACHE_KEY)
        if cached is not None:
            return cached
    data = _request('GET', '/device/listAll')
    cache.set(DEVICES_CACHE_KEY, data, DEVICES_TTL)
    return data


def list_devices_uuid():
    """장비 UUID 목록"""
    return _request('GET', '/device/listUUID')


def raw_collection_bulk(start_dt, end_dt, mosquito_count=None, device_uuid=None):
    """기간별 raw 포집 데이터
    start_dt, end_dt: ISO 8601 datetime 문자열
    """
    payload = {'startDateTime': start_dt, 'endDateTime': end_dt}
    if mosquito_count is not None:
        payload['mosquito_count'] = mosquito_count
    if device_uuid:
        payload['deviceUUID'] = device_uuid
    return _request('POST', '/device/rawCollectionBulk', json=payload)
