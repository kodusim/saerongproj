import re

import pytest

from test_public_routes import client


def csrf(client):
    return {'X-CSRFToken': client.cookies.get('csrftoken')}


def payload(client):
    page = client.get('/contact/')
    nonce = re.search(r'name="nonce" value="([^"]+)"', page.text).group(1)
    return dict(name='<script>alert(1)</script>', email='test@example.com',
                data='Synthetic CSV', service='Test inquiry only',
                consent=True, nonce=nonce)


def login(client):
    client.get('/admin/login/')
    response = client.post('/api/admin/login', headers=csrf(client),
                           json={'username': 'route-test', 'password': 'route-test-password'})
    assert response.status_code == 200


def test_inquiry_csrf_validation_persistence_and_idempotency(client):
    body = payload(client)
    assert client.post('/api/inquiries', json=body).status_code == 403
    assert client.post('/api/inquiries', headers=csrf(client), json={**body, 'consent': False}).status_code == 422
    assert client.post('/api/inquiries', headers=csrf(client), json={**body, 'name': '   '}).status_code == 422
    assert client.post('/api/inquiries', headers=csrf(client), json={**body, 'email': 'bad\r\nBcc:x@evil.com'}).status_code == 422
    assert client.post('/api/inquiries', headers=csrf(client), json={**body, 'nonce': 'invalid-token'}).status_code == 400
    response = client.post('/api/inquiries', headers=csrf(client), json=body)
    assert response.status_code == 201
    reference = response.json()['reference']
    retry = client.post('/api/inquiries', headers=csrf(client), json=body)
    assert retry.status_code == 200
    assert retry.json()['reference'] == reference
    from app.services.inquiries import list_inquiries
    rows, total = list_inquiries()
    assert total == 1
    assert rows[0]['mail'] == 'not_configured'
    assert 'email' not in response.json()


def test_admin_auth_escape_status_delete_and_logout(client):
    body = payload(client)
    reference = client.post('/api/inquiries', headers=csrf(client), json=body).json()['reference']
    assert client.get('/admin/', follow_redirects=False).status_code == 302
    assert client.post(f'/api/admin/inquiries/{reference}', headers=csrf(client), json={'status': 'read'}).status_code == 401
    login(client)
    response = client.get('/admin/')
    assert 'no-store' in response.headers['cache-control']
    assert 'noindex' in response.headers['x-robots-tag']
    assert '&lt;script&gt;' in response.text
    assert '<script>alert(1)</script>' not in response.text
    assert 'adsbygoogle' not in response.text
    assert client.post(f'/api/admin/inquiries/{reference}', headers=csrf(client), json={'status': 'replied'}).status_code == 200
    assert client.post(f'/api/admin/inquiries/{reference}', headers=csrf(client), json={'status': 'delete'}).status_code == 200
    assert client.post('/api/admin/logout', headers=csrf(client), json={}).status_code == 200
    assert client.get('/admin/', follow_redirects=False).status_code == 302
    # Administrator authentication does not grant access to medical data.
    assert client.get('/tdm/', follow_redirects=False).headers['location'] == '/tdm/login/'


def test_login_rate_limit_and_large_payload(client):
    client.get('/admin/login/')
    for _ in range(8):
        assert client.post('/api/admin/login', headers=csrf(client), json={'username':'bad','password':'bad'}).status_code == 401
    assert client.post('/api/admin/login', headers=csrf(client), json={}).status_code == 429
    assert client.post('/api/inquiries', headers=csrf(client), content='x'*25000).status_code == 413


@pytest.mark.parametrize('path', ['/travel', '/travel/seoul', '/portfolio/traffic/', '/privacy/', '/terms/', '/about/', '/ads.txt', '/sitemap.xml', '/robots.txt'])
def test_public_content_and_privacy(client, path, monkeypatch):
    from app.site_config import site_settings
    monkeypatch.setattr(site_settings, 'inquiry_to', 'private-owner@example.invalid')
    response = client.get(path)
    assert response.status_code == 200
    assert 'private-owner@example.invalid' not in response.text
    assert 'test@example.com' not in response.text


def test_ads_scope_and_travel_sources(client):
    # Rendering via the public hostname enables exactly one AdSense script.
    page = client.get('https://saerong.com/travel').text
    assert page.count('src="https://pagead2.googlesyndication.com') == 1
    for dataset in ('71776', '71778', '71779', '71780'):
        assert dataset in page
    assert '원본 여행로그는 아직 연결하지 않았고' in page
    assert 'adsbygoogle' not in client.get('https://saerong.com/contact/').text
    assert 'pub-7308084694640774' in client.get('/ads.txt').text
    assert '/admin/' not in client.get('/sitemap.xml').text
    assert client.get('/travel/', follow_redirects=False).status_code == 308
    assert client.get('/travel/not-a-place').status_code == 404


def test_notification_failure_keeps_inquiry(client, monkeypatch):
    from app.site_config import site_settings
    from app.services import inquiries
    for field, value in [('smtp_host','invalid'),('smtp_user','test'),('smtp_password','test'),('inquiry_to','owner@example.com')]:
        monkeypatch.setattr(site_settings, field, value)
    def fail(*args, **kwargs):
        raise OSError('network unavailable')
    monkeypatch.setattr(inquiries.smtplib, 'SMTP_SSL', fail)
    response = client.post('/api/inquiries', headers=csrf_after_contact(client), json=payload(client))
    assert response.status_code == 201
    rows, total = inquiries.list_inquiries()
    assert total == 1 and rows[0]['mail'] == 'failed'


def csrf_after_contact(client):
    client.get('/contact/')
    return csrf(client)


def test_production_admin_requires_dedicated_credentials(client, monkeypatch):
    import hashlib
    from app.config import settings
    from app.site_config import site_settings
    monkeypatch.setattr(settings, 'debug', False)
    monkeypatch.setattr(site_settings, 'site_admin_password_hash', '')
    client.get('/admin/login/')
    assert client.post('/api/admin/login', headers=csrf(client), json={
        'username': 'route-test', 'password': 'route-test-password',
    }).status_code == 401
    salt = b'test-only-admin-salt'
    digest = hashlib.pbkdf2_hmac('sha256', b'isolated-password', salt, 310000).hex()
    monkeypatch.setattr(site_settings, 'site_admin_user', 'site-admin')
    monkeypatch.setattr(site_settings, 'site_admin_password_hash', salt.hex() + ':' + digest)
    assert client.post('/api/admin/login', headers=csrf(client), json={
        'username': 'site-admin', 'password': 'isolated-password',
    }).status_code == 200
