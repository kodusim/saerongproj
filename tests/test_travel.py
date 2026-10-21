import csv
import json
from pathlib import Path
import sys

import pytest

from test_public_routes import client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_travel_catalog import build


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def records(tmp_path):
    travels, visits = [], []
    for i in range(15):
        travels.append({'TRAVEL_ID': f't{i}', 'TRAVELER_ID': f'private-person-{i}'})
        for name, kind in [('시험 공원', '1'), ('시험 박물관', '2'), ('비공개 집', '21')]:
            visits.append({'TRAVEL_ID': f't{i}', 'VISIT_AREA_ID': f'{name}-{i}', 'VISIT_AREA_NM': name,
                           'VISIT_AREA_TYPE_CD': kind, 'ROAD_NM_ADDR': '서울특별시 종로구 공개로 1',
                           'LOTNO_ADDR': '', 'X_COORD': '126.98', 'Y_COORD': '37.57', 'SGG_CD': '',
                           'DGSTFN': '' if i < 2 else '5' if kind == '1' else '3',
                           'RESIDENCE_TIME_MIN': '9999' if i == 0 else '60'})
    visits.append(dict(visits[0]))  # duplicate physical row
    travels.append({'TRAVEL_ID': 'repeat', 'TRAVELER_ID': 'private-person-0'})
    visits.append({**visits[0], 'TRAVEL_ID': 'repeat', 'VISIT_AREA_ID': 'repeat', 'DGSTFN':'1'})
    visits.append({**visits[0], 'VISIT_AREA_ID':'small', 'VISIT_AREA_NM':'소수 장소'})
    write_csv(tmp_path / 'tn_travel_test.csv', travels)
    write_csv(tmp_path / 'tn_visit_area_info_test.csv', visits)
    return tmp_path


def test_catalog_excludes_private_and_small_groups_and_repeated_travelers(records):
    data = build(records)
    assert len(data['places']) == 2
    park = next(p for p in data['places'] if p['category'] == 'nature')
    assert park['samples'] == 15
    assert park['rating_count'] == 13 and park['rating'] == 5
    assert park['histogram'] == [0, 0, 0, 0, 13]
    assert park['stay_count'] == 14 and park['stay_minutes'] == 60
    assert park['province'] == '서울'
    assert data['quality']['duplicate_rows'] == 1
    assert data['quality']['repeat_traveler_visits'] == 1
    serialized = json.dumps(data, ensure_ascii=False)
    assert 'private-person' not in serialized and '비공개 집' not in serialized
    assert 'TRAVEL_ID' not in serialized
    with pytest.raises(ValueError):
        build(records, minimum=1)


def test_missing_ratings_not_zero_and_sample_suppression(records):
    file = records / 'tn_visit_area_info_test.csv'
    with file.open(encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row['DGSTFN'] = ''
        row['RESIDENCE_TIME_MIN'] = '-1'
    write_csv(file, rows)
    data = build(records)
    assert all(p['rating'] is None and p['histogram'] is None and p['stay_minutes'] is None for p in data['places'])


@pytest.fixture
def populated(client, records, monkeypatch):
    from app.site_config import site_settings
    path = records / 'catalog.json'
    data = build(records)
    data['places'][0]['private_person'] = 'should-not-leak'
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(site_settings, 'travel_catalog', path)
    return client


def test_search_filters_detail_csv_and_no_raw_fields(populated):
    client = populated
    response = client.get('/api/travel/places?q=공원&province=서울&minimum=10')
    assert response.status_code == 200
    result = response.json()
    assert result['total'] == 1 and result['items'][0]['category'] == 'nature'
    assert 'should-not-leak' not in response.text
    place_id = result['items'][0]['id']
    assert client.get(f'/api/travel/places/{place_id}').json()['rating'] == 5
    assert client.get(f'/travel/{place_id}').status_code == 200
    assert '만족도 응답 분포' in client.get(f'/travel/{place_id}').text
    assert client.get('/api/travel/places?region=islands').json()['total'] == 0
    assert client.get('/api/travel/places?category=unknown').json()['total'] == 0
    assert client.get('/api/travel/places?ids=').json()['total'] == 0
    assert client.get(f'/api/travel/places?ids={place_id}').json()['total'] == 1
    assert client.get('/api/travel/places?sort=rating').json()['items'][0]['rating'] == 5
    assert client.get('/api/travel/places?page=999').json()['page'] == 1
    assert client.get('/api/travel/places?bounds=126,37,128,38').json()['total'] == 2
    assert client.get('/api/travel/places?bounds=nan,37,128,38').status_code == 422
    assert client.get('/api/travel/places?minimum=0').status_code == 422
    assert client.get('/api/travel/places?sort=invalid').status_code == 422
    assert client.get('/api/travel/places/not-found').status_code == 404
    export = client.get('/api/travel/export.csv?category=nature')
    assert export.status_code == 200 and export.content.startswith(b'\xef\xbb\xbf')
    assert '시험 공원' in export.text and '시험 박물관' not in export.text
    outside = client.get('/api/travel/export.csv?bounds=127,35,128,36')
    assert '시험 공원' not in outside.text
    assert client.get('/travel?bounds=127,35,128,36').status_code == 200
    assert '시험 공원' not in client.get('/travel?bounds=127,35,128,36').text
    page = client.get('/travel?q=공원').text
    assert '시험 공원' in page and '시험 박물관' not in page
    assert '원본 여행로그는 아직 연결하지 않았고' not in page
    assert '시험 공원' in client.get('/').text


def test_unavailable_catalog_and_csv_formula_guard(client):
    assert client.get('/api/travel/places').json()['meta']['available'] is False
    from app.services.travel import csv_export
    text = csv_export([dict(name='=1+1', address='@test', category_label='자연', samples=5,
                           rating=None, rating_count=0, stay_minutes=None, stay_count=0, year=2023)])
    assert "'=1+1" in text and "'@test" in text
