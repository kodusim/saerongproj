"""Public route migration checks; no database or ML inference is used."""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@127.0.0.1:1/unused')
    monkeypatch.setenv('DEBUG', 'true')
    from app.main import app
    from app.config import settings
    from app.db import get_session
    from app.site_config import site_settings
    monkeypatch.setattr(site_settings, 'site_store', tmp_path / 'inquiries.sqlite3')
    monkeypatch.setattr(site_settings, 'travel_catalog', tmp_path / 'missing-catalog.json')
    monkeypatch.setattr(site_settings, 'smtp_host', '')

    monkeypatch.setattr(settings, 'debug', True)
    monkeypatch.setattr(settings, 'tdm_auth_user', 'route-test')
    monkeypatch.setattr(settings, 'tdm_auth_password', 'route-test-password')

    async def no_database():
        yield None

    app.dependency_overrides[get_session] = no_database
    try:
        with TestClient(app, base_url='https://testserver') as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_home_and_retired_routes(client):
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 200
    assert '이번엔 어디?' in response.text
    assert '/static/css/public.css' in response.text
    assert '/static/js/public.js' in response.text
    for path in ['/work', '/work/', '/work/api/farm/state/', '/dusttest/', '/healthtest/', '/bltest/', '/api/analyze']:
        assert client.get(path).status_code == 404
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/work/ws'):
            pytest.fail('Retired Work websocket accepted a connection')
    assert client.get('/healthz').text == 'ok'


@pytest.mark.parametrize('path, page, title', [
    ('/', 'public', '새롱 — 데이터를 쓸모 있는 서비스로'),
    ('/portfolio/', 'portfolio', '데이터 분석·개발 포트폴리오 — 새롱'),
    ('/services/', 'services', '데이터 분석·대시보드·웹서비스 개발 — 새롱'),
    ('/contact/', 'contact', '개발 문의 — 새롱'),
])
def test_site_pages_render_without_javascript(client, path, page, title):
    response = client.get(path)
    assert response.status_code == 200
    assert f'<title>{title}</title>' in response.text
    assert f'href="{path}" aria-current="page"' in response.text


def test_tdm_auth_and_csrf_survive_move(client):
    assert client.get('/tdm', follow_redirects=False).headers['location'].endswith('/tdm/')
    assert client.get('/tdm/', follow_redirects=False).headers['location'] == '/tdm/login/'
    assert client.get('/tdm/logs/', follow_redirects=False).headers['location'] == '/tdm/login/'
    assert client.post('/tdm/api/predict/', json={}).status_code == 401
    assert client.get('/tdm/login/').status_code == 200
    credentials = {'username': 'route-test', 'password': 'route-test-password'}
    assert client.post('/tdm/login/', data=credentials).status_code == 403
    credentials['csrfmiddlewaretoken'] = client.cookies.get('csrftoken')
    response = client.post('/tdm/login/', data=credentials, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers['location'] == '/tdm/'
    page = client.get('/tdm/')
    assert page.status_code == 200
    assert '/tdmprediction/' not in page.text
    assert 'href="/tdm/logs/"' in page.text
    assert client.get('/tdm/logout/', follow_redirects=False).headers['location'] == '/tdm/login/'
    assert client.post('/tdm/api/predict/', json={}).status_code == 401


def test_legacy_links_and_post_redirects(client):
    response = client.get('/tdmprediction/logs/?view=recent', follow_redirects=False)
    assert response.status_code == 308
    assert response.headers['location'] == '/tdm/logs/?view=recent'
    assert client.get('/tdmprediction', follow_redirects=False).headers['location'] == '/tdm/'
    client.get('/tdm/login/')
    response = client.post('/tdmprediction/login/', data={
        'username': 'route-test',
        'password': 'route-test-password',
        'csrfmiddlewaretoken': client.cookies.get('csrftoken'),
    })
    assert [item.status_code for item in response.history] == [308, 302]
    assert response.status_code == 200
    assert response.url.path == '/tdm/'
    client.get('/tdm/logout/')
    assert client.post('/tdmprediction/api/predict/', json={}).status_code == 401
