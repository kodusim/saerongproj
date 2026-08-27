"""/bltest — BL 소설 플랫폼 1차 (인증 없는 프로토타입).

작가 구분은 `author_key` 로 한다 — 브라우저 localStorage 에 둔 랜덤 토큰이다.
IP 로 가르면 공유기 재접속만으로 작가가 작품 수정 권한을 잃기 때문이다.
키는 클라이언트가 만들어 `X-Author-Key` 헤더로 보낸다.

**지금은 공개 테스트라 키를 요구하지 않는다** (`OPEN_TEST`). 방문자 모두가
같은 공용 키를 쓰므로 누구나 글을 쓰고 아무 작품이나 고칠 수 있다. 테스트가
끝나면 `OPEN_TEST = False` 로 돌리면 원래의 키 소유 모델로 돌아간다.

**1차는 성인 등급(`adult`)을 받지 않는다.** 계정이 없어 연령을 확인할 방법이
없기 때문이다. 2차에서 계정 + 생년 확인이 붙은 뒤에 개방한다 (LB기획.md 참고).
"""
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import BlEpisode, BlReport, BlSeries
from app.security import client_ip
from app.templating import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/bltest', tags=['bl'])

MAX_SERIES = 200
MAX_TAGS = 8
MAX_BODY = 200_000        # 회차 본문 상한 (약 20만 자)

# 1차에서 허용하는 등급 — 'adult' 는 연령 확인 수단이 없어 제외한다.
ALLOWED_RATINGS = ('all', 'teen')

AUTHOR_KEY_RE = re.compile(r'^[A-Za-z0-9_-]{16,64}$')

# 공개 테스트 — 키 없이도 글을 쓸 수 있게 모두를 같은 작가로 취급한다.
OPEN_TEST = True
OPEN_TEST_KEY = 'bltest-open-shared-key'   # AUTHOR_KEY_RE 를 통과하는 고정 키


def author_key(request: Request) -> str:
    """작가 키 — 형식이 맞지 않으면 빈 문자열(= 권한 없음).

    테스트 중에는 헤더를 보지 않고 공용 키를 준다. 그래야 예전에 만들어 둔
    localStorage 키가 남아 있는 브라우저에서도 남의 작품을 고칠 수 있다.
    """
    if OPEN_TEST:
        return OPEN_TEST_KEY
    key = (request.headers.get('x-author-key') or '').strip()
    return key if AUTHOR_KEY_RE.match(key) else ''


def owns(series, key: str) -> bool:
    """이 작품을 고칠 수 있는가. 테스트 중에는 (예전 키로 만든 작품까지)
    누구나 고칠 수 있다."""
    if OPEN_TEST:
        return True
    return bool(key) and series.author_key == key


def mine_badge(series, key: str) -> bool:
    """'내 작품' 배지를 달지 — 테스트 중에는 모두가 모두의 작가라 달지 않는다.
    (권한 판정은 owns() 로 따로 한다.)"""
    return False if OPEN_TEST else owns(series, key)


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


# ------------------------------------------------------------------ 페이지

@router.get('/', response_class=HTMLResponse)
async def bl_home(request: Request):
    return templates.TemplateResponse(request, 'bl/home.html', {})


@router.get('/write', response_class=HTMLResponse)
async def bl_write(request: Request):
    return templates.TemplateResponse(request, 'bl/write.html', {})


@router.get('/s/{series_id}', response_class=HTMLResponse)
async def bl_series_page(request: Request, series_id: int):
    return templates.TemplateResponse(request, 'bl/series.html', {'series_id': series_id})


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
    """목록. `mine=1` 이면 내 작가 키의 작품만 (임시저장 포함)."""
    key = author_key(request)

    stmt = select(BlSeries)
    if mine and not OPEN_TEST:
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
    key = author_key(request)
    if not key:
        return JSONResponse({'error': '작가 키가 없습니다.'}, status_code=400)

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
        author_name=(data.get('author_name') or '익명').strip()[:32] or '익명',
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
    s.author_name = (data.get('author_name') or '익명').strip()[:32] or '익명'
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
    # 테스트 중에는 모두가 작가라서, 그대로 두면 조회수가 아예 늘지 않는다.
    if (OPEN_TEST or not mine) and e.published_at is not None:
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
