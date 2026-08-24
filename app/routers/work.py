"""/work — 실시간 채팅 + 게시판 + 구글 스칼라 검색.

JSON 응답 형태는 Django 판과 완전히 동일하다 (프런트를 손대지 않기 위해).
"""
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import WorkChatMessage, WorkPost
from app.security import client_ip
from app.services import storage
from app.services.scholar import ScholarBlockedError, search_scholar
from app.templating import templates

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


def _post_json(p: WorkPost, with_body: bool = False) -> dict:
    data = {
        'id': p.id,
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

    return JSONResponse({'id': msg.id, 'created_at': msg.created_at.isoformat()})


# ---------------------------------------------------------------- 게시판

@router.get('/api/posts/')
async def api_posts(
    request: Request,
    category: str = '',
    q: str = '',
    session: AsyncSession = Depends(get_session),
):
    stmt = select(WorkPost).order_by(desc(WorkPost.created_at))
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

    category = data.get('category')
    if category not in WorkPost.CATEGORY_LABELS:
        category = 'novel'

    post = WorkPost(
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
