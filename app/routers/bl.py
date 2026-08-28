"""/bltest — 알카포스트 (BL 소설 연재 플랫폼) 프로토타입.

**작가는 계정으로 가른다.** 회원가입은 없다 — 운영자가 `BL_USERS` 에 직접
넣어 아이디/비밀번호를 부여한다. 로그인하면 세션에 아이디가 남고, 계정마다
고정된 `author_key` 가 작품 소유를 판정한다.

읽기는 로그인 없이 누구나 한다. **글쓰기·수정·삭제만 로그인을 요구한다.**

공개 테스트 시절(`LEGACY_OPEN_KEY`)에 방문자들이 공용 키로 쓴 작품이 남아
있다. 그 키를 가진 계정이 없으므로 지금은 아무도 고칠 수 없다 — 읽기 전용이다.

**성인 등급(`adult`)은 아직 받지 않는다.** 생년 확인 절차가 없기 때문이다.
계정이 생겼으니 2차에서 생년을 받으면 열 수 있다 (LB기획.md 참고).
"""
import hashlib
import logging
import re
import secrets
import unicodedata
from datetime import datetime, timezone
from typing import NamedTuple

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import BlEpisode, BlReport, BlSeries
from app.security import BL_SESSION_KEY, client_ip, verify_form_csrf
from app.templating import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/bltest', tags=['bl'])

MAX_SERIES = 200
MAX_TAGS = 8
MAX_BODY = 200_000        # 회차 본문 상한 (약 20만 자)

# 1차에서 허용하는 등급 — 'adult' 는 연령 확인 수단이 없어 제외한다.
ALLOWED_RATINGS = ('all', 'teen')

AUTHOR_KEY_RE = re.compile(r'^[A-Za-z0-9_-]{16,64}$')

# 공개 테스트 시절 방문자 모두가 공유하던 키. 이 키로 쓰인 작품은 주인이 없다.
LEGACY_OPEN_KEY = 'bltest-open-shared-key'

LOGIN_URL = '/bltest/login'
HOME_URL = '/bltest/'
WRITE_URL = '/bltest/write'

# ------------------------------------------------------------------ 계정
#
# 회원가입은 없다. 운영자가 아래 표에 직접 넣어 아이디/비밀번호를 부여한다.
# 비밀번호는 평문으로 두지 않고 pbkdf2-sha256 해시만 둔다. 새 비밀번호는 이렇게
# 만든다 (앞이 salt, 뒤가 pw_hash):
#
#   python -c "import hashlib,secrets; s=secrets.token_hex(16); print(s,
#     hashlib.pbkdf2_hmac('sha256', '새비번'.encode(), bytes.fromhex(s), 200_000).hex())"
#
# `key` 는 작품 소유를 판정하는 author_key 다. AUTHOR_KEY_RE 를 통과해야 하고
# **한 번 정하면 바꾸지 않는다** — 바꾸면 그 계정이 쓴 작품이 전부 남의 것이 된다.

PBKDF2_ROUNDS = 200_000


class _Acct(NamedTuple):
    id: int
    key: str
    salt: str
    pw_hash: str


BL_USERS: dict[str, _Acct] = {
    '전상기': _Acct(
        1, 'arca-user-000001',
        '057aec5d8c25b04e82ddfdf61d3e18bd',
        'a78f45fef9e747c92ef33601f47e9391c93bc13fc1bcd22e83bd2f2f4c1cca8c',
    ),
    '박지우': _Acct(
        2, 'arca-user-000002',
        'b8904f0f0ad313e43d3eea6f47c3c33c',
        'af829397b91f8d3f50650d8716c7dd78613cbe5e1daf95e174087d3ca48e9535',
    ),
    '배지원': _Acct(
        3, 'arca-user-000003',
        'c922abe5ee5b62fc7d393fe063d7ba1f',
        '7a6f52dc802b1fccfb52fda934f71d342cf1b2ab7e0e32bb0a362e9125dd6eeb',
    ),
}


def _pw_ok(raw: str, acct: _Acct) -> bool:
    got = hashlib.pbkdf2_hmac(
        'sha256', raw.encode(), bytes.fromhex(acct.salt), PBKDF2_ROUNDS
    ).hex()
    return secrets.compare_digest(got, acct.pw_hash)


def normalize_id(raw: str) -> str:
    """아이디 정규화.

    아이디가 한글이라 NFC 로 합쳐 준다 — macOS 는 한글을 자모로 분해(NFD)해서
    보내는 경우가 있어, 눈에 똑같이 보여도 사전 키와 안 맞는다.
    """
    return unicodedata.normalize('NFC', (raw or '').strip())


def current_user(request: Request) -> str:
    """로그인한 아이디. 비로그인이면 빈 문자열.

    세션에 남아 있어도 `BL_USERS` 에서 지운 계정이면 로그아웃된 것으로 본다.
    """
    name = normalize_id(request.session.get(BL_SESSION_KEY) or '')
    return name if name in BL_USERS else ''


def author_key(request: Request) -> str:
    """작가 키 = 로그인한 계정의 고정 키. 비로그인이면 빈 문자열(= 권한 없음)."""
    name = current_user(request)
    return BL_USERS[name].key if name else ''


def owns(series, key: str) -> bool:
    """이 작품을 고칠 수 있는가.

    공용 키로 쓰인 옛 작품(LEGACY_OPEN_KEY)은 어떤 계정의 키와도 같지 않으므로
    저절로 읽기 전용이 된다 — 따로 분기하지 않는다.
    """
    return bool(key) and series.author_key == key


def mine_badge(series, key: str) -> bool:
    """'내 작품' 배지를 달지."""
    return owns(series, key)


def _publish_now(flag) -> datetime | None:
    """publish 플래그가 참이면 지금 시각, 아니면 None(임시저장)."""
    return datetime.now(timezone.utc) if flag else None


def _clean_tags(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    out = []
    for t in raw:
        t = str(t).strip()[:20]
        if t and t not in out:
            out.append(t)
        if len(out) >= MAX_TAGS:
            break
    return out


def _series_json(s: BlSeries, mine: bool = False, episodes: int = 0) -> dict:
    return {
        'id': s.id,
        'author_name': s.author_name,
        'title': s.title,
        'summary': s.summary,
        'tags': s.tags or [],
        'rating': s.rating,
        'rating_label': s.rating_label,
        'status': s.status,
        'status_label': s.status_label,
        'views': s.views,
        'episodes': episodes,
        'mine': mine,
        'created_at': s.created_at.isoformat(),
        'updated_at': s.updated_at.isoformat(),
    }


def _episode_json(e: BlEpisode, with_body: bool = False) -> dict:
    data = {
        'id': e.id,
        'series_id': e.series_id,
        'no': e.no,
        'title': e.title,
        'published': e.published_at is not None,
        'published_at': e.published_at.isoformat() if e.published_at else None,
        'views': e.views,
        'updated_at': e.updated_at.isoformat(),
    }
    if with_body:
        data['body'] = e.body
    return data


# ------------------------------------------------------------------ 로그인

@router.get('/login', response_class=HTMLResponse)
async def bl_login_page(request: Request):
    if current_user(request):
        return RedirectResponse(WRITE_URL, status_code=302)
    return templates.TemplateResponse(request, 'bl/login.html', {'err': ''})


@router.post('/login', response_class=HTMLResponse)
async def bl_login_submit(
    request: Request,
    username: str = Form(''),
    password: str = Form(''),
    csrfmiddlewaretoken: str = Form(''),
):
    # 이 경로는 CSRF 미들웨어가 건너뛴다 (폼은 헤더를 못 붙인다) — 여기서 직접 본다.
    verify_form_csrf(request, csrfmiddlewaretoken)

    name = normalize_id(username)
    acct = BL_USERS.get(name)
    if acct is not None and _pw_ok(password, acct):
        # 세션 쿠키는 TDM 과 공유한다 — clear() 하면 TDM 로그인까지 풀린다.
        request.session[BL_SESSION_KEY] = name
        logger.info('bl login ok user=%s ip=%s', name, client_ip(request))
        return RedirectResponse(WRITE_URL, status_code=302)

    logger.warning('bl login fail user=%r ip=%s', name[:32], client_ip(request))
    return templates.TemplateResponse(
        request,
        'bl/login.html',
        {'err': '아이디 또는 비밀번호가 올바르지 않습니다.'},
        status_code=401,
    )


@router.get('/logout')
async def bl_logout(request: Request):
    request.session.pop(BL_SESSION_KEY, None)
    return RedirectResponse(HOME_URL, status_code=302)


# ------------------------------------------------------------------ 페이지

@router.get('/', response_class=HTMLResponse)
async def bl_home(request: Request):
    return templates.TemplateResponse(
        request, 'bl/home.html', {'user': current_user(request)}
    )


@router.get('/write', response_class=HTMLResponse)
async def bl_write(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(LOGIN_URL, status_code=302)
    return templates.TemplateResponse(request, 'bl/write.html', {'user': user})


@router.get('/s/{series_id}', response_class=HTMLResponse)
async def bl_series_page(request: Request, series_id: int):
    return templates.TemplateResponse(
        request, 'bl/series.html',
        {'series_id': series_id, 'user': current_user(request)},
    )


@router.get('/s/{series_id}/{no}', response_class=HTMLResponse)
async def bl_viewer_page(request: Request, series_id: int, no: int):
    return templates.TemplateResponse(
        request, 'bl/viewer.html', {'series_id': series_id, 'no': no}
    )


# ------------------------------------------------------------------ 작품

@router.get('/api/series/')
async def api_series_list(
    request: Request,
    q: str = '',
    tag: str = '',
    sort: str = 'new',
    mine: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """목록. `mine=1` 이면 로그인한 계정의 작품만 (임시저장 포함)."""
    key = author_key(request)

    stmt = select(BlSeries)
    if mine:
        if not key:
            return JSONResponse({'series': [], 'my_key': ''})
        stmt = stmt.where(BlSeries.author_key == key)

    q = (q or '').strip()
    if q:
        stmt = stmt.where(BlSeries.title.ilike(f'%{q}%'))
    tag = (tag or '').strip()
    if tag:
        stmt = stmt.where(BlSeries.tags.contains([tag]))

    stmt = stmt.order_by(
        desc(BlSeries.views) if sort == 'popular' else desc(BlSeries.updated_at)
    )

    rows = (await session.scalars(stmt.limit(MAX_SERIES))).all()

    # 작품별 공개 회차 수 — 목록에서 "N화" 를 보여주려고 한 번에 센다
    counts = {}
    if rows:
        count_rows = await session.execute(
            select(BlEpisode.series_id, func.count(BlEpisode.id))
            .where(
                BlEpisode.series_id.in_([s.id for s in rows]),
                BlEpisode.published_at.is_not(None),
            )
            .group_by(BlEpisode.series_id)
        )
        counts = dict(count_rows.all())

    return JSONResponse({
        'series': [
            _series_json(s, mine=mine_badge(s, key), episodes=counts.get(s.id, 0))
            for s in rows
        ],
    })


@router.post('/api/series/create/')
async def api_series_create(request: Request, session: AsyncSession = Depends(get_session)):
    user = current_user(request)
    if not user:
        return JSONResponse({'error': '로그인이 필요합니다.'}, status_code=401)
    key = BL_USERS[user].key

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)

    title = (data.get('title') or '').strip()[:200]
    if not title:
        return JSONResponse({'error': '작품 제목을 입력하세요.'}, status_code=400)

    rating = data.get('rating') or 'all'
    if rating not in ALLOWED_RATINGS:
        return JSONResponse({
            'error': '이 사이트는 아직 연령 확인 기능이 없어 성인 등급 작품을 '
                     '등록할 수 없습니다. 전체이용가 또는 15세로 지정해주세요.',
        }, status_code=400)

    status = data.get('status') or 'ongoing'
    if status not in BlSeries.STATUSES:
        status = 'ongoing'

    item = BlSeries(
        author_key=key,
        author_user_id=BL_USERS[user].id,
        # 필명은 계정 아이디와 별개다 — 비워 두면 아이디를 그대로 쓴다.
        author_name=(data.get('author_name') or '').strip()[:32] or user,
        title=title,
        summary=(data.get('summary') or '')[:2000],
        tags=_clean_tags(data.get('tags')),
        rating=rating,
        status=status,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return JSONResponse(_series_json(item, mine=True), status_code=201)


@router.get('/api/series/{series_id}/')
async def api_series_detail(
    request: Request, series_id: int, session: AsyncSession = Depends(get_session)
):
    s = await session.get(BlSeries, series_id)
    if s is None:
        return JSONResponse({'error': '작품을 찾을 수 없습니다.'}, status_code=404)

    key = author_key(request)
    mine = owns(s, key)

    stmt = select(BlEpisode).where(BlEpisode.series_id == series_id)
    if not mine:
        # 임시저장은 작가에게만 보인다
        stmt = stmt.where(BlEpisode.published_at.is_not(None))
    eps = (await session.scalars(stmt.order_by(BlEpisode.no))).all()

    published = sum(1 for e in eps if e.published_at is not None)
    return JSONResponse({
        'series': _series_json(s, mine=mine_badge(s, key), episodes=published),
        'episodes': [_episode_json(e) for e in eps],
    })


@router.post('/api/series/{series_id}/')
async def api_series_update(
    request: Request, series_id: int, session: AsyncSession = Depends(get_session)
):
    key = author_key(request)
    s = await session.get(BlSeries, series_id)
    if s is None:
        return JSONResponse({'error': '작품을 찾을 수 없습니다.'}, status_code=404)
    if not owns(s, key):
        return JSONResponse({'error': '이 작품을 수정할 권한이 없습니다.'}, status_code=403)

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)

    title = (data.get('title') or '').strip()[:200]
    if not title:
        return JSONResponse({'error': '작품 제목을 입력하세요.'}, status_code=400)

    rating = data.get('rating') or s.rating
    if rating not in ALLOWED_RATINGS:
        return JSONResponse({
            'error': '이 사이트는 아직 연령 확인 기능이 없어 성인 등급 작품을 '
                     '등록할 수 없습니다.',
        }, status_code=400)

    status = data.get('status') or s.status
    if status not in BlSeries.STATUSES:
        status = s.status

    s.title = title
    # 필명을 비우면 원래 필명을 지운 게 아니라 계정 아이디로 되돌린다.
    s.author_name = (data.get('author_name') or '').strip()[:32] or current_user(request)
    s.summary = (data.get('summary') or '')[:2000]
    s.tags = _clean_tags(data.get('tags'))
    s.rating = rating
    s.status = status

    await session.commit()
    await session.refresh(s)
    return JSONResponse(_series_json(s, mine=True))


@router.delete('/api/series/{series_id}/')
async def api_series_delete(
    request: Request, series_id: int, session: AsyncSession = Depends(get_session)
):
    key = author_key(request)
    s = await session.get(BlSeries, series_id)
    if s is None:
        return JSONResponse({'error': '작품을 찾을 수 없습니다.'}, status_code=404)
    if not owns(s, key):
        return JSONResponse({'error': '이 작품을 삭제할 권한이 없습니다.'}, status_code=403)

    # 회차는 FK ondelete=CASCADE 로 같이 지워진다
    await session.delete(s)
    await session.commit()
    return JSONResponse({'deleted': True})


# ------------------------------------------------------------------ 회차

@router.get('/api/series/{series_id}/ep/{no}/')
async def api_episode_detail(
    request: Request, series_id: int, no: int,
    session: AsyncSession = Depends(get_session),
):
    s = await session.get(BlSeries, series_id)
    if s is None:
        return JSONResponse({'error': '작품을 찾을 수 없습니다.'}, status_code=404)

    key = author_key(request)
    mine = owns(s, key)

    e = (await session.scalars(
        select(BlEpisode).where(
            BlEpisode.series_id == series_id, BlEpisode.no == no
        )
    )).one_or_none()
    if e is None or (e.published_at is None and not mine):
        return JSONResponse({'error': '회차를 찾을 수 없습니다.'}, status_code=404)

    # 조회수는 경합을 피해 DB 에서 직접 증가시킨다 (작가 본인은 세지 않는다).
    if not mine and e.published_at is not None:
        await session.execute(
            update(BlEpisode).where(BlEpisode.id == e.id)
            .values(views=BlEpisode.views + 1)
        )
        await session.commit()
        e.views += 1

    # 이전/다음 화 — 공개된 것만 (작가에게는 임시저장도)
    nav_stmt = select(BlEpisode.no).where(BlEpisode.series_id == series_id)
    if not mine:
        nav_stmt = nav_stmt.where(BlEpisode.published_at.is_not(None))
    nos = sorted((await session.scalars(nav_stmt)).all())
    idx = nos.index(e.no) if e.no in nos else -1

    return JSONResponse({
        'series': _series_json(s, mine=mine_badge(s, key)),
        'episode': _episode_json(e, with_body=True),
        'prev': nos[idx - 1] if idx > 0 else None,
        'next': nos[idx + 1] if 0 <= idx < len(nos) - 1 else None,
    })


@router.post('/api/series/{series_id}/ep/create/')
async def api_episode_create(
    request: Request, series_id: int, session: AsyncSession = Depends(get_session)
):
    key = author_key(request)
    s = await session.get(BlSeries, series_id)
    if s is None:
        return JSONResponse({'error': '작품을 찾을 수 없습니다.'}, status_code=404)
    if not owns(s, key):
        return JSONResponse({'error': '이 작품에 회차를 쓸 권한이 없습니다.'}, status_code=403)

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)

    title = (data.get('title') or '').strip()[:200]
    if not title:
        return JSONResponse({'error': '회차 제목을 입력하세요.'}, status_code=400)

    # 다음 회차 번호 — 작품 안에서 유일해야 한다
    last = (await session.scalars(
        select(func.max(BlEpisode.no)).where(BlEpisode.series_id == series_id)
    )).one()

    e = BlEpisode(
        series_id=series_id,
        no=(last or 0) + 1,
        title=title,
        body=(data.get('body') or '')[:MAX_BODY],
        published_at=_publish_now(data.get('publish')),
    )
    session.add(e)
    # 작품 목록 정렬(최신 갱신순)을 위해 작품도 건드린다
    s.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(e)
    return JSONResponse(_episode_json(e, with_body=True), status_code=201)


@router.post('/api/series/{series_id}/ep/{no}/')
async def api_episode_update(
    request: Request, series_id: int, no: int,
    session: AsyncSession = Depends(get_session),
):
    key = author_key(request)
    s = await session.get(BlSeries, series_id)
    if s is None:
        return JSONResponse({'error': '작품을 찾을 수 없습니다.'}, status_code=404)
    if not owns(s, key):
        return JSONResponse({'error': '이 회차를 수정할 권한이 없습니다.'}, status_code=403)

    e = (await session.scalars(
        select(BlEpisode).where(
            BlEpisode.series_id == series_id, BlEpisode.no == no
        )
    )).one_or_none()
    if e is None:
        return JSONResponse({'error': '회차를 찾을 수 없습니다.'}, status_code=404)

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)

    title = (data.get('title') or '').strip()[:200]
    if not title:
        return JSONResponse({'error': '회차 제목을 입력하세요.'}, status_code=400)

    e.title = title
    e.body = (data.get('body') or '')[:MAX_BODY]
    # publish 를 명시적으로 보냈을 때만 공개 상태를 바꾼다.
    # 이미 공개된 회차를 다시 공개해도 최초 공개 시각은 유지한다.
    if 'publish' in data:
        if data.get('publish'):
            e.published_at = e.published_at or datetime.now(timezone.utc)
        else:
            e.published_at = None

    s.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(e)
    return JSONResponse(_episode_json(e, with_body=True))


@router.delete('/api/series/{series_id}/ep/{no}/')
async def api_episode_delete(
    request: Request, series_id: int, no: int,
    session: AsyncSession = Depends(get_session),
):
    key = author_key(request)
    s = await session.get(BlSeries, series_id)
    if s is None:
        return JSONResponse({'error': '작품을 찾을 수 없습니다.'}, status_code=404)
    if not owns(s, key):
        return JSONResponse({'error': '이 회차를 삭제할 권한이 없습니다.'}, status_code=403)

    e = (await session.scalars(
        select(BlEpisode).where(
            BlEpisode.series_id == series_id, BlEpisode.no == no
        )
    )).one_or_none()
    if e is None:
        return JSONResponse({'error': '회차를 찾을 수 없습니다.'}, status_code=404)

    await session.delete(e)
    await session.commit()
    return JSONResponse({'deleted': True})


# ------------------------------------------------------------------ 신고

@router.post('/api/report/')
async def api_report(request: Request, session: AsyncSession = Depends(get_session)):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)

    target_type = data.get('target_type')
    if target_type not in BlReport.TARGETS:
        return JSONResponse({'error': '잘못된 신고 대상입니다.'}, status_code=400)
    try:
        target_id = int(data.get('target_id'))
    except (TypeError, ValueError):
        return JSONResponse({'error': '잘못된 신고 대상입니다.'}, status_code=400)

    reason = data.get('reason')
    if reason not in BlReport.REASONS:
        reason = 'etc'

    session.add(BlReport(
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        detail=(data.get('detail') or '')[:2000],
        reporter_ip=client_ip(request),
    ))
    await session.commit()
    return JSONResponse({'ok': True}, status_code=201)
