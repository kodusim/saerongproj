"""Public website, travel discovery and a separate authenticated inquiry inbox."""
import json
import hashlib
import hmac
import re
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response
from itsdangerous import URLSafeTimedSerializer, BadSignature
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config import settings
from app.site_config import site_settings
from app.services import inquiries, travel as travel_data
from app.services.site_content import DESTINATIONS, PROJECTS, REGIONS
from app.templating import templates

router = APIRouter()


def travel_bounds(value):
    if not value:
        return None
    try:
        box = [float(v) for v in value.split(',')]
        if len(box) != 4 or not (124 <= box[0] < box[2] <= 132 and 32 <= box[1] < box[3] <= 40):
            raise ValueError
        return box
    except ValueError:
        raise HTTPException(422, '지도 검색 범위를 확인해주세요.')


def render(request, name, title, description, page='public', ads=False, **context):
    canonical = site_settings.site_origin.rstrip('/') + request.url.path
    return templates.TemplateResponse(request, f'site/{name}.html', {
        'title': title, 'description': description, 'page': page, 'ads': ads,
        'canonical': canonical, 'projects': PROJECTS, 'regions': REGIONS,
        'destinations': DESTINATIONS, **context,
    })


@router.get('/')
def index(request: Request):
    return render(request, 'index', '새롱 — 데이터를 쓸모 있는 서비스로',
                  '국내 여행 기록 탐색과 데이터 분석 프로젝트. 데이터를 정리하고 분석해 누구나 쓰는 웹서비스로 만듭니다.',
                  ads=True, travel_overview=travel_data.search(per_page=3))


@router.get('/travel')
def travel(request: Request, q: str = Query('', max_length=100), region: str = '',
           province: str = '', category: str = '', minimum: int = Query(5, ge=5, le=1000),
           sort: Literal['samples', 'rating', 'name'] = 'samples', page: int = Query(1, ge=1),
           bounds: str = Query('', max_length=120)):
    results = travel_data.search(q=q, region=region, province=province, category=category,
                                 minimum=minimum, sort=sort, page=page, bounds=travel_bounds(bounds))
    return render(request, 'travel', '이번엔 어디? — 여행 기록으로 찾는 국내 여행 | 새롱',
                  '실제 여행 기록에서 장소를 찾고, 방문 표본과 만족도를 비교해 나만의 여행 후보를 정리하세요.',
                  ads=True, results=results, filters=dict(q=q, region=region, province=province,
                                                        category=category, minimum=minimum, sort=sort))


@router.get('/api/travel/places')
def travel_places(q: str = Query('', max_length=100), region: str = '', province: str = '',
                  category: str = '', minimum: int = Query(5, ge=5, le=1000),
                  sort: Literal['samples', 'rating', 'name'] = 'samples', page: int = Query(1, ge=1),
                  ids: str | None = Query(None, max_length=1500), bounds: str = Query('', max_length=120)):
    box = travel_bounds(bounds)
    return travel_data.search(q=q, region=region, province=province, category=category,
                              minimum=minimum, sort=sort, page=page,
                              ids=ids.split(',') if ids is not None else None, bounds=box)


@router.get('/api/travel/places/{place_id}')
def travel_place(place_id: str):
    item = travel_data.place(place_id)
    if not item:
        raise HTTPException(404, '장소를 찾을 수 없습니다.')
    return item


@router.get('/api/travel/export.csv')
def travel_export(q: str = Query('', max_length=100), region: str = '', province: str = '',
                  category: str = '', minimum: int = Query(5, ge=5, le=1000),
                  sort: Literal['samples', 'rating', 'name'] = 'samples', bounds: str = Query('', max_length=120)):
    results = travel_data.search(q=q, region=region, province=province, category=category,
                                 minimum=minimum, sort=sort, per_page=10000, bounds=travel_bounds(bounds))
    return Response(travel_data.csv_export(results['items']), media_type='text/csv',
                    headers={'Content-Disposition': 'attachment; filename="travel-2023.csv"'})


@router.get('/travel/')
def travel_slash():
    return RedirectResponse('/travel', status_code=308)


@router.get('/travel/{slug}')
def destination(request: Request, slug: str):
    if slug.startswith('p-'):
        item = travel_data.place(slug)
        if not item:
            raise HTTPException(404, '장소를 찾을 수 없습니다.')
        return render(request, 'travel_place', f"{item['name']} — 여행 기록 | 새롱",
                      f"{item['name']}의 2023년 방문 표본과 만족도 기록을 확인하세요.",
                      ads=True, item=item)
    item = next((d for d in DESTINATIONS if d['id'] == slug), None)
    if not item:
        raise HTTPException(404, '여행지를 찾을 수 없습니다.')
    return render(request, 'destination', f"{item['name']} 여행 가이드 — 새롱", item['text'],
                  ads=True, item=item, map_query=quote(item['name']))


@router.get('/portfolio/')
def portfolio(request: Request):
    return render(request, 'portfolio', '데이터 분석·개발 포트폴리오 — 새롱',
                  '환경 관측, 교통량, 가격 분석과 업무 자동화. 작업 자료를 바탕으로 재구성한 분석·개발 사례를 살펴보세요.', page='portfolio')


@router.get('/portfolio/{slug}/')
def case_study(request: Request, slug: str):
    item = next((p for p in PROJECTS if p['id'] == slug), None)
    if not item:
        raise HTTPException(404, '프로젝트를 찾을 수 없습니다.')
    return render(request, 'case', f"{item['title']} — 포트폴리오 | 새롱",
                  item['summary'], page='portfolio', item=item)


@router.get('/services/')
def services(request: Request):
    return render(request, 'services', '데이터 분석·대시보드·웹서비스 개발 — 새롱',
                  '엑셀 정제, 데이터 분석, 시각화, 예측 모델과 웹서비스 개발. 필요한 단계부터 범위와 산출물을 함께 정합니다.', page='services')


def signer():
    return URLSafeTimedSerializer(settings.secret_key, salt='site-inquiry-v1')


@router.get('/contact/')
def contact(request: Request):
    nonce = signer().dumps(secrets.token_hex(16))
    response = render(request, 'contact', '개발 문의 — 새롱', '보유 데이터와 만들고 싶은 서비스를 알려주세요. 문의는 비공개로 접수됩니다.',
                      page='contact', nonce=nonce)
    response.headers['Cache-Control'] = 'no-store'
    return response


class Inquiry(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    data: str = Field(min_length=1, max_length=3000)
    service: str = Field(min_length=1, max_length=5000)
    timeline: str = Field(default='', max_length=100)
    budget: str = Field(default='', max_length=100)
    consent: Literal[True]
    website: str = Field(default='', max_length=200)
    nonce: str = Field(min_length=10, max_length=300)

    @field_validator('name', 'email', 'data', 'service', 'timeline', 'budget', mode='before')
    @classmethod
    def strip_text(cls, value):
        if not isinstance(value, str):
            raise ValueError('문자열을 입력하세요.')
        return value.strip()

    @field_validator('email')
    @classmethod
    def email_format(cls, value):
        if not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}', value):
            raise ValueError('이메일 형식을 확인하세요.')
        return value


async def read_json(request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 24000:
            raise HTTPException(413, '입력 내용이 너무 깁니다.')
    try:
        result = json.loads(body)
        if not isinstance(result, dict):
            raise ValueError
        return result
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, '올바른 요청을 보내주세요.')


def client_ip(request):
    # Uvicorn trusts forwarded headers only from the configured local nginx proxy.
    return request.client.host if request.client else 'unknown'


@router.post('/api/inquiries')
async def submit(request: Request, tasks: BackgroundTasks):
    try:
        body = Inquiry.model_validate(await read_json(request))
    except ValidationError:
        return JSONResponse({'error': '필수 항목, 이메일 형식과 개인정보 수집 동의를 확인해주세요.'}, status_code=422)
    try:
        signer().loads(body.nonce, max_age=7200)
    except BadSignature:
        return JSONResponse({'error': '접수 화면이 만료되었습니다. 새로고침 후 다시 제출해주세요.'}, status_code=400)
    if body.website:
        return JSONResponse({'error': '요청을 처리할 수 없습니다.'}, status_code=400)
    if not await run_in_threadpool(inquiries.rate_limit, client_ip(request), 'inquiry', 5, 3600):
        return JSONResponse({'error': '잠시 후 다시 문의해주세요. 시간당 접수 횟수를 초과했습니다.'}, status_code=429)
    reference, created = await run_in_threadpool(inquiries.create_inquiry, body.model_dump())
    if created:
        tasks.add_task(inquiries.notify, reference)
    return JSONResponse({'reference': reference, 'message': '문의가 접수되었습니다. 접수번호를 보관해주세요.'},
                        status_code=201 if created else 200, headers={'Cache-Control': 'no-store'})


def admin_authed(request):
    timestamp = request.session.get('site_admin_at', 0)
    return isinstance(timestamp, (int, float)) and 0 <= time.time() - timestamp < 7200


def private(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    return response


@router.get('/admin/')
async def admin(request: Request, page: int = 1):
    if not admin_authed(request):
        return private(RedirectResponse('/admin/login/', status_code=302))
    page = max(1, min(page, 100000))
    rows, total = await run_in_threadpool(inquiries.list_inquiries, page)
    for row in rows:
        row['date'] = datetime.fromtimestamp(row['created'], timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
    return private(render(request, 'admin', '문의 관리 — 새롱', '', page='admin',
                          rows=rows, total=total, current_page=page, noindex=True))


@router.get('/admin/login/')
def admin_login(request: Request):
    return private(render(request, 'admin_login', '관리자 로그인 — 새롱', '', page='admin', noindex=True))


@router.post('/api/admin/login')
async def admin_login_submit(request: Request):
    body = await read_json(request)
    if not await run_in_threadpool(inquiries.rate_limit, client_ip(request), 'login', 8, 900):
        return private(JSONResponse({'error': '로그인 시도가 많습니다. 15분 후 다시 시도하세요.'}, status_code=429))
    username, password = body.get('username', ''), body.get('password', '')
    if not isinstance(username, str) or not isinstance(password, str) or len(username) > 200 or len(password) > 500:
        raise HTTPException(400)
    valid = False
    if site_settings.site_admin_password_hash:
        try:
            salt, expected = site_settings.site_admin_password_hash.split(':', 1)
            actual = await run_in_threadpool(hashlib.pbkdf2_hmac, 'sha256', password.encode(), bytes.fromhex(salt), 310000)
            valid = hmac.compare_digest(actual.hex(), expected) and secrets.compare_digest(username.encode(), site_settings.site_admin_user.encode())
        except ValueError:
            valid = False
    elif settings.debug:
        # Isolated development only; production always requires a dedicated credential.
        valid = secrets.compare_digest(username.encode(), settings.tdm_auth_user.encode()) and secrets.compare_digest(password.encode(), settings.tdm_auth_password.encode())
    if valid:
        request.session['site_admin_at'] = time.time()
        return private(JSONResponse({'ok': True}))
    return private(JSONResponse({'error': '아이디 또는 비밀번호를 확인해주세요.'}, status_code=401))


@router.post('/api/admin/logout')
async def admin_logout(request: Request):
    request.session.pop('site_admin_at', None)
    return private(JSONResponse({'ok': True}))


@router.post('/api/admin/inquiries/{reference}')
async def admin_update(request: Request, reference: str):
    if not admin_authed(request):
        return private(JSONResponse({'error': '로그인이 필요합니다.'}, status_code=401))
    body = await read_json(request)
    status = body.get('status')
    if status not in ('new', 'read', 'replied', 'closed', 'delete'):
        raise HTTPException(400, '처리 상태를 확인해주세요.')
    count = await run_in_threadpool(inquiries.update_inquiry, reference, status)
    if not count:
        raise HTTPException(404, '문의를 찾을 수 없습니다.')
    return private(JSONResponse({'ok': True}))


@router.get('/privacy/')
@router.get('/terms/')
@router.get('/about/')
def policy(request: Request):
    kind = request.url.path.strip('/')
    title = {'privacy': '개인정보처리방침', 'terms': '이용안내', 'about': '새롱 소개'}[kind]
    return render(request, 'policy', f'{title} — 새롱', title, kind=kind, policy_title=title)


@router.get('/ads.txt', response_class=PlainTextResponse)
def ads_txt():
    return 'google.com, pub-7308084694640774, DIRECT, f08c47fec0942fa0\n'


@router.get('/robots.txt', response_class=PlainTextResponse)
def robots():
    return f'User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /api/\nDisallow: /tdm/\nDisallow: /tdmprediction/\nSitemap: {site_settings.site_origin}/sitemap.xml\n'


@router.get('/sitemap.xml')
def sitemap():
    paths = ['/', '/travel', '/portfolio/', '/services/', '/contact/', '/about/', '/privacy/', '/terms/']
    paths += [f"/travel/{d['id']}" for d in DESTINATIONS]
    paths += [f"/portfolio/{p['id']}/" for p in PROJECTS]
    body = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    body += ''.join(f'<url><loc>{site_settings.site_origin}{p}</loc></url>' for p in paths) + '</urlset>'
    return Response(body, media_type='application/xml')
