"""/tdmprediction — 반코마이신 하이브리드(ML+DL) 농도 예측."""
import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import PredictionLog
from app.security import (
    TDM_LOGIN_ID_KEY,
    TDM_SESSION_KEY,
    is_tdm_authed,
    tdm_login_id,
    verify_form_csrf,
)
from app.templating import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/tdmprediction', tags=['tdm'])

LOGIN_URL = '/tdmprediction/login/'
PREDICT_URL = '/tdmprediction/'


@router.get('/login/', response_class=HTMLResponse)
async def login_page(request: Request):
    if is_tdm_authed(request):
        return RedirectResponse(PREDICT_URL, status_code=302)
    return templates.TemplateResponse(request, 'tdm/login.html', {'err': ''})


@router.post('/login/', response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: str = Form(''),
    password: str = Form(''),
    csrfmiddlewaretoken: str = Form(''),
):
    verify_form_csrf(request, csrfmiddlewaretoken)

    if username.strip() == settings.tdm_auth_user and password.strip() == settings.tdm_auth_password:
        request.session[TDM_SESSION_KEY] = True
        request.session[TDM_LOGIN_ID_KEY] = username.strip()
        return RedirectResponse(PREDICT_URL, status_code=302)

    return templates.TemplateResponse(
        request,
        'tdm/login.html',
        {'err': '아이디 또는 비밀번호가 올바르지 않습니다.'},
    )


@router.get('/logout/')
async def logout(request: Request):
    for key in (TDM_SESSION_KEY, TDM_LOGIN_ID_KEY):
        request.session.pop(key, None)
    return RedirectResponse(LOGIN_URL, status_code=302)


@router.get('/', response_class=HTMLResponse)
async def predict_page(request: Request):
    if not is_tdm_authed(request):
        return RedirectResponse(LOGIN_URL, status_code=302)
    return templates.TemplateResponse(
        request, 'tdm/predict.html', {'login_id': tdm_login_id(request)}
    )


@router.post('/api/predict/')
async def predict_api(request: Request, session: AsyncSession = Depends(get_session)):
    if not is_tdm_authed(request):
        return JSONResponse({'error': '로그인이 필요합니다.'}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({'error': '잘못된 JSON'}, status_code=400)
    if not isinstance(body, dict):
        return JSONResponse({'error': '잘못된 JSON'}, status_code=400)

    try:
        dose_mg = float(body.get('dose_mg') or 1000)
        q_hr = float(body.get('q_hr') or 12)
        n_doses = max(1, min(40, int(body.get('n_doses') or 10)))
    except (TypeError, ValueError):
        return JSONResponse({'error': '용량/간격/횟수 형식이 올바르지 않습니다.'}, status_code=400)

    if dose_mg <= 0 or q_hr <= 0:
        return JSONResponse({'error': '용량/간격은 0보다 커야 합니다.'}, status_code=400)

    from app.services import predictor as tdm_predictor

    try:
        # 추론은 CPU 바운드(sklearn + torch) — 이벤트 루프를 막지 않도록 스레드로 보낸다.
        result = await run_in_threadpool(
            tdm_predictor.predict_tdm,
            patient=body.get('patient') or {},
            dose_mg=dose_mg,
            q_hr=q_hr,
            n_doses=n_doses,
        )
    except FileNotFoundError as exc:
        return JSONResponse({'error': f'모델 파일 누락: {exc}'}, status_code=500)
    except Exception as exc:
        logger.exception('TDM 예측 실패')
        return JSONResponse({'error': str(exc)}, status_code=500)

    # 감사 로그 — 실패해도 예측 결과는 돌려준다.
    try:
        meta = result.get('model_meta') or {}
        session.add(
            PredictionLog(
                login_id=tdm_login_id(request),
                input_json=body,
                result_json=result,
                ml_model=meta.get('ml_model') or '',
                dl_model=meta.get('dl_model') or '',
            )
        )
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception('PredictionLog 저장 실패 (계속 진행)')

    return JSONResponse(result)


@router.get('/logs/', response_class=HTMLResponse)
async def logs_page(request: Request, session: AsyncSession = Depends(get_session)):
    """예측 감사 로그 조회 — Django admin 을 대신하는 읽기전용 페이지."""
    if not is_tdm_authed(request):
        return RedirectResponse(LOGIN_URL, status_code=302)

    rows = (
        await session.execute(
            select(PredictionLog).order_by(desc(PredictionLog.created_at)).limit(200)
        )
    ).scalars().all()

    return templates.TemplateResponse(
        request,
        'tdm/logs.html',
        {'login_id': tdm_login_id(request), 'rows': rows},
    )
