"""/work — 실시간 채팅 + 게시판 + 일정 + 구글 스칼라 검색."""
import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect

from app.config import settings
from app.db import get_session
from app.models import WorkChatMessage, WorkPost, WorkSchedule
from app.security import client_ip
from app.services import storage
from app.services.scholar import ScholarBlockedError, search_scholar
from app.templating import templates
from app.ws import hub

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/work', tags=['work'])

MAX_MESSAGES = 200
MAX_POSTS = 300


def _ip_str(value: Any) -> str:
    """asyncpg 는 inet 컬럼을 ipaddress 객체로 돌려준다."""
    return '' if value is None else str(value)


def _message_json(m: WorkChatMessage) -> dict:
    return {
        'id': m.id,
        'sender_name': m.sender_name,
        'body': m.body,
        'image_url': f"{settings.media_url}{m.image}" if m.image else None,
        'created_at': m.created_at.isoformat(),
        'sender_ip': _ip_str(m.sender_ip),
    }


def _board_or_default(value: str) -> str:
    value = (value or '').strip()
    return value if value in WorkPost.BOARDS else 'archive'


def _post_json(p: WorkPost, with_body: bool = False) -> dict:
    data = {
        'id': p.id,
        'board': p.board,
        'category': p.category,
        'category_label': p.category_label,
        'title': p.title,
        'author_name': p.author_name,
        'author_ip': _ip_str(p.author_ip),
        'views': p.views,
        'created_at': p.created_at.isoformat(),
        'updated_at': p.updated_at.isoformat(),
    }
    if with_body:
        data['body'] = p.body
    return data


@router.get('/', response_class=HTMLResponse)
async def work_page(request: Request):
    return templates.TemplateResponse(request, 'work/page.html', {})


# ---------------------------------------------------------------- 채팅

@router.get('/api/messages/')
async def api_messages(
    request: Request,
    after: int = 0,
    session: AsyncSession = Depends(get_session),
):
    if after < 0:
        after = 0
    rows = (
        await session.execute(
            select(WorkChatMessage)
            .where(WorkChatMessage.id > after)
            .order_by(WorkChatMessage.id)
            .limit(MAX_MESSAGES)
        )
    ).scalars().all()

    return JSONResponse({
        'my_ip': client_ip(request),
        'messages': [_message_json(m) for m in rows],
    })


@router.post('/api/send/')
async def api_send(
    request: Request,
    sender_name: str = Form('익명'),
    body: str = Form(''),
    image: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    sender_name = (sender_name or '익명').strip()[:32] or '익명'
    body = (body or '').strip()[:2000]

    has_image = bool(image and image.filename)
    if not body and not has_image:
        return JSONResponse({'error': '내용 또는 이미지를 입력하세요.'}, status_code=400)

    stored_path = None
    if has_image:
        try:
            stored_path = await storage.save_chat_image(image)
        except storage.ImageTooLargeError:
            return JSONResponse({'error': '이미지는 8MB 이하만 첨부할 수 있습니다.'}, status_code=400)
        except storage.InvalidImageError:
            return JSONResponse({'error': '올바른 이미지 파일이 아닙니다.'}, status_code=400)

    msg = WorkChatMessage(
        sender_name=sender_name,
        sender_ip=client_ip(request),
        body=body,
        image=stored_path,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)

    # 접속 중인 모든 클라이언트에게 밀어준다 (실패해도 저장은 성공이므로 무시)
    try:
        await hub.broadcast({'type': 'messages', 'messages': [_message_json(msg)]})
    except Exception:
        logger.exception('WebSocket 브로드캐스트 실패 (계속 진행)')

    return JSONResponse({'id': msg.id, 'created_at': msg.created_at.isoformat()})


@router.websocket('/ws')
async def chat_ws(ws: WebSocket):
    """채팅 실시간 수신 전용 채널.

    클라이언트는 이 소켓으로 보내지 않는다 — 전송은 HTTP POST /api/send/ 다.
    여기서 receive 를 계속 기다리는 건 연결 종료를 감지하기 위해서다.
    """
    await hub.connect(ws)
    try:
        await ws.send_json({'type': 'hello', 'my_ip': client_ip(ws)})
        while True:
            # ping 등 클라이언트가 보내는 건 버린다
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.debug('WebSocket 종료', exc_info=True)
    finally:
        await hub.disconnect(ws)


# ---------------------------------------------------------------- 게시판

@router.get('/api/posts/')
async def api_posts(
    request: Request,
    board: str = 'archive',
    category: str = '',
    q: str = '',
    session: AsyncSession = Depends(get_session),
):
    stmt = select(WorkPost).order_by(desc(WorkPost.created_at))
    stmt = stmt.where(WorkPost.board == _board_or_default(board))
    category = (category or '').strip()
    if category:
        stmt = stmt.where(WorkPost.category == category)
    q = (q or '').strip()
    if q:
        stmt = stmt.where(WorkPost.title.ilike(f'%{q}%'))

    rows = (await session.execute(stmt.limit(MAX_POSTS))).scalars().all()
    return JSONResponse({
        'my_ip': client_ip(request),
        'posts': [_post_json(p) for p in rows],
    })


@router.post('/api/posts/create/')
async def api_post_create(request: Request, session: AsyncSession = Depends(get_session)):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)

    title = (data.get('title') or '').strip()[:200]
    if not title:
        return JSONResponse({'error': '제목을 입력하세요.'}, status_code=400)

    board = _board_or_default(data.get('board') or '')
    category = data.get('category')
    if category not in WorkPost.CATEGORY_LABELS:
        category = 'notice' if board == 'notice' else 'novel'

    post = WorkPost(
        board=board,
        category=category,
        title=title,
        author_name=(data.get('author_name') or '익명').strip()[:32] or '익명',
        author_ip=client_ip(request),
        body=data.get('body') or '',
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return JSONResponse(_post_json(post, with_body=True), status_code=201)


async def _get_post_or_404(session: AsyncSession, post_id: int) -> WorkPost | None:
    return (
        await session.execute(select(WorkPost).where(WorkPost.id == post_id))
    ).scalar_one_or_none()


@router.get('/api/posts/{post_id}/')
async def api_post_detail(post_id: int, session: AsyncSession = Depends(get_session)):
    post = await _get_post_or_404(session, post_id)
    if post is None:
        return JSONResponse({'error': '게시글을 찾을 수 없습니다.'}, status_code=404)

    # 조회수는 경합을 피해 DB 에서 직접 증가시킨다.
    await session.execute(
        update(WorkPost).where(WorkPost.id == post_id).values(views=WorkPost.views + 1)
    )
    await session.commit()
    post.views += 1
    return JSONResponse(_post_json(post, with_body=True))


@router.post('/api/posts/{post_id}/')
async def api_post_update(
    post_id: int, request: Request, session: AsyncSession = Depends(get_session)
):
    post = await _get_post_or_404(session, post_id)
    if post is None:
        return JSONResponse({'error': '게시글을 찾을 수 없습니다.'}, status_code=404)

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)

    title = (data.get('title') or '').strip()[:200]
    if not title:
        return JSONResponse({'error': '제목을 입력하세요.'}, status_code=400)

    category = data.get('category')
    if category in WorkPost.CATEGORY_LABELS:
        post.category = category
    post.title = title
    post.author_name = (data.get('author_name') or '익명').strip()[:32] or '익명'
    post.body = data.get('body') or ''

    await session.commit()
    await session.refresh(post)
    return JSONResponse(_post_json(post, with_body=True))


@router.delete('/api/posts/{post_id}/')
async def api_post_delete(post_id: int, session: AsyncSession = Depends(get_session)):
    post = await _get_post_or_404(session, post_id)
    if post is None:
        return JSONResponse({'error': '게시글을 찾을 수 없습니다.'}, status_code=404)
    await session.delete(post)
    await session.commit()
    return JSONResponse({'deleted': True})


# ------------------------------------------------------------------- 일정

def _schedule_json(s: WorkSchedule) -> dict:
    return {
        'id': s.id,
        'title': s.title,
        'meet_date': s.meet_date.date().isoformat(),
        'meet_time': s.meet_time,
        'place': s.place,
        'attendees': s.attendees,
        'memo': s.memo,
        'author_name': s.author_name,
        'author_ip': _ip_str(s.author_ip),
        'created_at': s.created_at.isoformat(),
    }


def _parse_meet_date(raw: str) -> datetime | None:
    """`YYYY-MM-DD` 만 받는다 (input[type=date] 값)."""
    try:
        d = date.fromisoformat((raw or '').strip())
    except ValueError:
        return None
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _schedule_fields(data: dict) -> tuple[dict | None, str]:
    """폼 값 검증 → (필드 dict, 에러메시지)."""
    title = (data.get('title') or '').strip()[:200]
    if not title:
        return None, '일정 제목을 입력하세요.'

    meet_date = _parse_meet_date(data.get('meet_date') or '')
    if meet_date is None:
        return None, '날짜를 YYYY-MM-DD 형식으로 입력하세요.'

    return {
        'title': title,
        'meet_date': meet_date,
        'meet_time': (data.get('meet_time') or '').strip()[:16],
        'place': (data.get('place') or '').strip()[:120],
        'attendees': (data.get('attendees') or '').strip()[:200],
        'memo': data.get('memo') or '',
        'author_name': (data.get('author_name') or '익명').strip()[:32] or '익명',
    }, ''


@router.get('/api/schedules/')
async def api_schedules(request: Request, session: AsyncSession = Depends(get_session)):
    """가까운 날짜부터. 지난 일정도 그대로 보여준다 (기록이므로)."""
    rows = (await session.scalars(
        select(WorkSchedule).order_by(WorkSchedule.meet_date, WorkSchedule.meet_time)
    )).all()
    return JSONResponse({
        'my_ip': client_ip(request),
        'schedules': [_schedule_json(s) for s in rows],
    })


@router.post('/api/schedules/create/')
async def api_schedule_create(request: Request, session: AsyncSession = Depends(get_session)):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)

    fields, err = _schedule_fields(data)
    if fields is None:
        return JSONResponse({'error': err}, status_code=400)

    item = WorkSchedule(**fields, author_ip=client_ip(request))
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return JSONResponse(_schedule_json(item), status_code=201)


@router.post('/api/schedules/{schedule_id}/')
async def api_schedule_update(
    schedule_id: int, request: Request, session: AsyncSession = Depends(get_session)
):
    item = await session.get(WorkSchedule, schedule_id)
    if item is None:
        return JSONResponse({'error': '일정을 찾을 수 없습니다.'}, status_code=404)

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({'error': '잘못된 요청입니다.'}, status_code=400)

    fields, err = _schedule_fields(data)
    if fields is None:
        return JSONResponse({'error': err}, status_code=400)

    for key, value in fields.items():
        setattr(item, key, value)

    await session.commit()
    await session.refresh(item)
    return JSONResponse(_schedule_json(item))


@router.delete('/api/schedules/{schedule_id}/')
async def api_schedule_delete(schedule_id: int, session: AsyncSession = Depends(get_session)):
    item = await session.get(WorkSchedule, schedule_id)
    if item is None:
        return JSONResponse({'error': '일정을 찾을 수 없습니다.'}, status_code=404)
    await session.delete(item)
    await session.commit()
    return JSONResponse({'deleted': True})


# ---------------------------------------------------------------- 스칼라 검색

@router.get('/api/scholar/')
async def api_scholar(q: str = ''):
    q = (q or '').strip()
    if not q:
        return JSONResponse({'results': [], 'stats': ''})

    fallback = f'https://scholar.google.com/scholar?q={q}'
    try:
        data = await search_scholar(q)
    except ScholarBlockedError:
        return JSONResponse({
            'error': '구글이 검색 요청을 일시적으로 차단했습니다. 잠시 후 다시 시도하거나 아래 링크로 직접 검색하세요.',
            'fallback_url': fallback,
        }, status_code=502)
    except Exception:
        logger.exception('scholar search failed: %s', q)
        return JSONResponse({
            'error': '검색 중 오류가 발생했습니다.',
            'fallback_url': fallback,
        }, status_code=502)
    return JSONResponse(data)
