"""Read an aggregate-only travel catalog; never query original visitor records."""
import csv
from functools import lru_cache
import io
import json

from app.site_config import site_settings

CATEGORIES = {'nature': '자연·산책', 'culture': '문화·역사', 'shopping': '시장·쇼핑',
              'activity': '체험·레저', 'food': '식당·카페'}
REGIONS = {'capital': '수도권', 'east': '동부권', 'west': '서부권', 'islands': '제주'}
FIELDS = ('id', 'name', 'address', 'province', 'region', 'category', 'category_label',
          'lat', 'lng', 'samples', 'rating_count', 'rating', 'histogram', 'stay_count',
          'stay_minutes', 'source', 'year', 'adjusted_rating')


@lru_cache(maxsize=2)
def _read(path, modified):
    with open(path, encoding='utf-8') as stream:
        catalog = json.load(stream)
    if catalog.get('version') != 1:
        raise ValueError('Unsupported travel catalog')
    # Allowlist fields so a later preprocessing change cannot expose raw records.
    places = [{key: p.get(key) for key in FIELDS} for p in catalog['places']
              if p.get('samples', 0) >= 5 and p.get('category') in CATEGORIES]
    return {'places': places, 'year': catalog['year'], 'built_at': catalog['built_at'],
            'prior_mean': catalog['prior_mean'], 'prior_weight': catalog['prior_weight'],
            'datasets': catalog['datasets'], 'available': True}


def catalog():
    path = site_settings.travel_catalog
    try:
        return _read(str(path), path.stat().st_mtime_ns)
    except (OSError, ValueError, KeyError, TypeError):
        return {'places': [], 'year': 2023, 'available': False, 'datasets': [71776, 71778, 71779, 71780]}


def search(q='', region='', province='', category='', minimum=5, sort='samples',
           page=1, per_page=24, ids=None, bounds=None):
    data = catalog()
    places = data['places']
    terms = q.casefold().split()
    selected = set(ids) if ids is not None else None
    results = [p for p in places if
               (not terms or all(t in (p['name'] + ' ' + p['address']).casefold() for t in terms)) and
               (not region or p['region'] == region) and
               (not province or p['province'] == province) and
               (not category or p['category'] == category) and p['samples'] >= minimum and
               (selected is None or p['id'] in selected) and
               (not bounds or bounds[0] <= p['lng'] <= bounds[2] and bounds[1] <= p['lat'] <= bounds[3])]
    if sort == 'rating':
        results.sort(key=lambda p: (-(p['adjusted_rating'] or 0), -p['samples'], p['id']))
    elif sort == 'name':
        results.sort(key=lambda p: (p['name'], p['id']))
    else:
        results.sort(key=lambda p: (-p['samples'], p['name'], p['id']))
    total = len(results)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(max(1, page), pages)
    return {'items': results[(page - 1) * per_page:page * per_page], 'total': total,
            'page': page, 'pages': pages, 'per_page': per_page,
            'map_items': [{k: p[k] for k in ('id', 'name', 'lat', 'lng', 'samples', 'category')}
                          for p in results[:300]], 'map_limited': total > 300,
            'meta': {k: v for k, v in data.items() if k != 'places'},
            'catalog_total': len(places),
            'provinces': sorted({p['province'] for p in places}),
            'categories': CATEGORIES, 'regions': REGIONS}


def place(place_id):
    return next((p for p in catalog()['places'] if p['id'] == place_id), None)


def csv_export(items):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['장소', '주소', '분류', '방문표본수_여행자별1회', '만족도평균_5점',
                     '만족도응답수', '체류중앙값_분', '체류응답수', '기록연도', '출처'])
    for p in items:
        values = [p['name'], p['address'], p['category_label'], p['samples'], p['rating'],
                  p['rating_count'], p['stay_minutes'], p['stay_count'], p['year'], 'AI허브 국내 여행로그']
        writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for v in values])
    return '\ufeff' + stream.getvalue()
