"""Open-Meteo 기반 날씨 동기화.

- /forecast (실황): 현재 기온/습도/강수량/풍속
- /geocoding/v1/search: 주소 텍스트 → 위경도 (lat/lng 0 인 장비용 fallback)

API 키 불필요, 완전 무료.
"""
import logging
import requests
from django.utils import timezone
from django.core.cache import cache

from .models import Device

logger = logging.getLogger(__name__)

FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
GEOCODE_URL = 'https://geocoding-api.open-meteo.com/v1/search'
GEOCODE_CACHE_TTL = 30 * 86400  # 30일


def _geocode(query):
    """주소 문자열 → (lat, lng). 못 찾으면 None."""
    if not query:
        return None
    key = f'moscom:geocode:{query}'
    cached = cache.get(key)
    if cached is not None:
        return cached if cached else None
    try:
        r = requests.get(GEOCODE_URL, params={'name': query, 'count': 1, 'language': 'ko'}, timeout=8)
        r.raise_for_status()
        data = r.json()
        results = data.get('results') or []
        if not results:
            cache.set(key, '', GEOCODE_CACHE_TTL)
            return None
        lat = float(results[0].get('latitude'))
        lng = float(results[0].get('longitude'))
        cache.set(key, (lat, lng), GEOCODE_CACHE_TTL)
        return (lat, lng)
    except Exception as e:
        logger.warning(f'geocode failed for {query!r}: {e}')
        return None


def _resolve_latlng(d):
    """장비의 위경도 결정. lat/lng 가 0 이면 주소로 geocoding."""
    if d.latitude and d.longitude and abs(d.latitude) > 0.1 and abs(d.longitude) > 0.1:
        return (d.latitude, d.longitude)
    # 주소 텍스트로 geocoding 시도
    parts = [p for p in [d.address_sido, d.address_gungu, d.address_dong] if p]
    if not parts:
        return None
    addr = ' '.join(parts)
    return _geocode(addr)


def _fetch_weather_batch(coords):
    """Open-Meteo 한 번에 여러 좌표 조회.
    coords: [(lat, lng), ...]
    Returns: dict {(lat, lng): {temperature, humidity, precipitation, wind_speed}}
    """
    if not coords:
        return {}
    # Open-Meteo는 lat/lng 콤마 구분 다중 좌표 지원
    lats = ','.join(f'{lat:.4f}' for lat, _ in coords)
    lngs = ','.join(f'{lng:.4f}' for _, lng in coords)
    params = {
        'latitude': lats, 'longitude': lngs,
        'current': 'temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m',
        'timezone': 'Asia/Seoul',
    }
    try:
        r = requests.get(FORECAST_URL, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f'open-meteo failed: {e}')
        return {}
    # 단일 좌표면 dict, 여러면 list
    if isinstance(data, dict):
        data = [data]
    out = {}
    for i, item in enumerate(data):
        if i >= len(coords):
            break
        cur = item.get('current') or {}
        out[coords[i]] = {
            'temperature': cur.get('temperature_2m'),
            'humidity': cur.get('relative_humidity_2m'),
            'precipitation': cur.get('precipitation'),
            'wind_speed': cur.get('wind_speed_10m'),
        }
    return out


def sync_weather():
    """모든 활성 장비의 날씨 데이터 갱신. 1시간 주기."""
    devices = list(Device.objects.filter(is_active=True))
    # 1) 좌표 결정
    dev_coords = {}
    coord_set = []
    for d in devices:
        c = _resolve_latlng(d)
        if c:
            dev_coords[d.id] = c
            if c not in coord_set:
                coord_set.append(c)

    # 2) 좌표 배치로 날씨 조회 (Open-Meteo는 100개 정도까지 한 호출 가능)
    weather_map = {}
    BATCH = 50
    for i in range(0, len(coord_set), BATCH):
        chunk = coord_set[i:i + BATCH]
        weather_map.update(_fetch_weather_batch(chunk))

    # 3) 장비별로 저장
    now = timezone.now()
    n_updated = 0
    for d in devices:
        c = dev_coords.get(d.id)
        if not c:
            continue
        w = weather_map.get(c)
        if not w:
            continue
        d.temperature = w.get('temperature')
        d.humidity = w.get('humidity')
        d.precipitation = w.get('precipitation')
        d.wind_speed = w.get('wind_speed')
        d.weather_synced_at = now
        d.save(update_fields=['temperature', 'humidity', 'precipitation', 'wind_speed', 'weather_synced_at'])
        n_updated += 1

    logger.info(f'sync_weather: {n_updated}/{len(devices)} devices updated')
    return {'updated': n_updated, 'total': len(devices), 'coord_count': len(coord_set)}
