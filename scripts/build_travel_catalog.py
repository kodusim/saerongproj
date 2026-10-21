"""Build a public place-level catalog from private AIHub 2023 CSVs.

Only public visit types with >=5 distinct travelers are published. No personal
identifiers, trajectories, free-text travel titles, or individual rows leave this job.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {'1': 'nature', '2': 'culture', '3': 'culture', '4': 'shopping',
              '5': 'activity', '6': 'activity', '7': 'nature', '8': 'culture',
              '10': 'shopping', '11': 'food', '13': 'activity'}
LABELS = {'nature': '자연·산책', 'culture': '문화·역사', 'shopping': '시장·쇼핑',
          'activity': '체험·레저', 'food': '식당·카페'}
PROVINCES = {'11': '서울', '26': '부산', '27': '대구', '28': '인천', '29': '광주',
             '30': '대전', '31': '울산', '36': '세종', '41': '경기', '42': '강원',
             '51': '강원', '43': '충북', '44': '충남', '45': '전북', '52': '전북',
             '46': '전남', '47': '경북', '48': '경남', '50': '제주'}
REGIONS = {'서울': 'capital', '경기': 'capital', '인천': 'capital', '강원': 'east',
           '경북': 'east', '경남': 'east', '부산': 'east', '대구': 'east', '울산': 'east',
           '충북': 'west', '충남': 'west', '전북': 'west', '전남': 'west', '광주': 'west',
           '대전': 'west', '세종': 'west', '제주': 'islands'}
ADDRESS_PROVINCES = {'서울': '서울', '부산': '부산', '대구': '대구', '인천': '인천',
                     '광주': '광주', '대전': '대전', '울산': '울산', '세종': '세종',
                     '경기': '경기', '강원': '강원', '충청북': '충북', '충북': '충북',
                     '충청남': '충남', '충남': '충남', '전라북': '전북', '전북': '전북',
                     '전라남': '전남', '전남': '전남', '경상북': '경북', '경북': '경북',
                     '경상남': '경남', '경남': '경남', '제주': '제주'}


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        yield from csv.DictReader(stream)


def number(value, low, high):
    try:
        result = float(value)
        return result if math.isfinite(result) and low <= result <= high else None
    except (TypeError, ValueError):
        return None


def normalized(value):
    return re.sub(r'\s+', '', value).casefold()


def build(root, minimum=5):
    if minimum < 5:
        raise ValueError('Minimum public sample size must be at least 5.')
    travelers = {}
    for file in sorted(root.rglob('tn_travel_*.csv')):
        for row in read_csv(file):
            if row.get('TRAVELER_ID'):
                travelers[row['TRAVEL_ID']] = row['TRAVELER_ID']
    groups = defaultdict(dict)
    quality = Counter()
    seen = set()
    for file in sorted(root.rglob('tn_visit_area_info_*.csv')):
        for row in read_csv(file):
            quality['input_rows'] += 1
            record = (row.get('TRAVEL_ID'), row.get('VISIT_AREA_ID'))
            if record in seen:
                quality['duplicate_rows'] += 1
                continue
            seen.add(record)
            kind = CATEGORIES.get(row.get('VISIT_AREA_TYPE_CD'))
            name = row.get('VISIT_AREA_NM', '').strip()
            address = (row.get('ROAD_NM_ADDR') or row.get('LOTNO_ADDR') or '').strip()
            person = travelers.get(row.get('TRAVEL_ID'))
            lat = number(row.get('Y_COORD'), 33, 39)
            lng = number(row.get('X_COORD'), 124, 132)
            province = PROVINCES.get(row.get('SGG_CD', '')[:2])
            if not province:
                province = next((v for k, v in ADDRESS_PROVINCES.items() if address.startswith(k)), None)
            if not kind or not name or not address or not person or lat is None or lng is None or not province:
                quality['excluded_rows'] += 1
                continue
            # Exact name/address match: do not merge different branches or infer aliases.
            identity = '|'.join((normalized(name), normalized(address), kind))
            group = groups[identity]
            if person in group:
                quality['repeat_traveler_visits'] += 1
                continue
            group[person] = {'name': name, 'address': address, 'lat': lat, 'lng': lng,
                             'province': province, 'category': kind,
                             'rating': number(row.get('DGSTFN'), 1, 5),
                             'stay': number(row.get('RESIDENCE_TIME_MIN'), 1, 720)}
    places = []
    for identity, people in groups.items():
        if len(people) < minimum:
            quality['small_sample_places'] += 1
            continue
        rows = list(people.values())
        first = rows[0]
        ratings = [int(r['rating']) for r in rows if r['rating'] is not None and r['rating'].is_integer()]
        stays = [r['stay'] for r in rows if r['stay'] is not None]
        histogram = [ratings.count(i) for i in range(1, 6)] if len(ratings) >= minimum else None
        places.append({'id': 'p-' + hashlib.sha256(identity.encode()).hexdigest()[:16],
                       'name': first['name'], 'address': first['address'],
                       'province': first['province'], 'region': REGIONS[first['province']],
                       'category': first['category'], 'category_label': LABELS[first['category']],
                       'lat': round(median(r['lat'] for r in rows), 5),
                       'lng': round(median(r['lng'] for r in rows), 5),
                       'samples': len(rows), 'rating_count': len(ratings),
                       'rating': round(mean(ratings), 2) if histogram else None,
                       'histogram': histogram, 'stay_count': len(stays),
                       'stay_minutes': round(median(stays)) if len(stays) >= minimum else None,
                       'source': 'aihub', 'year': 2023})
    rated = [p for p in places if p['rating'] is not None]
    total = sum(p['rating_count'] for p in rated)
    prior = sum(sum((i + 1) * n for i, n in enumerate(p['histogram'])) for p in rated) / total if total else 0
    for place in places:
        n, rating = place['rating_count'], place['rating']
        place['adjusted_rating'] = round((sum((i + 1) * count for i, count in enumerate(place['histogram'])) + 20 * prior) / (n + 20), 4) if rating is not None else None
    places.sort(key=lambda p: (-p['samples'], p['name'], p['id']))
    return {'version': 1, 'year': 2023, 'source': 'AI허브 국내 여행로그 2023',
            'built_at': datetime.now(timezone.utc).isoformat(), 'minimum_samples': minimum,
            'prior_mean': round(prior, 4), 'prior_weight': 20,
            'datasets': [71776, 71778, 71779, 71780], 'quality': dict(quality), 'places': places}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'private_data/travel/raw')
    parser.add_argument('--output', type=Path, default=ROOT / 'private_data/travel/catalog.json')
    args = parser.parse_args()
    catalog = build(args.input)
    if not catalog['places']:
        raise SystemExit('No eligible places. Existing catalog was not replaced.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(json.dumps(catalog, ensure_ascii=False), encoding='utf-8')
    temporary.replace(args.output)
    print(json.dumps({'places': len(catalog['places']), 'quality': catalog['quality']}, ensure_ascii=True))


if __name__ == '__main__':
    main()
