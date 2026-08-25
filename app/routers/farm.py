"""/work/api/farm — 농사 게임.

규칙과 시간 계산은 전부 `app/services/farm.py` 에 있다. 여기서는 요청을 받아
농장을 찾아오고, 행동을 시키고, 새 상태를 돌려주는 것만 한다.
"""
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import cast, desc, select
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import WorkFarm, WorkGameSave
from app.security import client_ip
from app.services import farm as rules

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/work/api/farm', tags=['farm'])

RANKING_LIMIT = 20


def _by_ip(ip: str):
    """`inet = varchar` 연산자가 없어서 명시적으로 캐스팅해야 한다.
    (기존 코드는 INET 에 넣기만 했지 비교한 적이 없어 안 드러났던 부분)"""
    return WorkFarm.owner_ip == cast(ip, INET)


async def _get_or_create(request: Request, session: AsyncSession) -> WorkFarm:
    ip = client_ip(request)
    found = await session.scalar(select(WorkFarm).where(_by_ip(ip)))
    if found:
        return found

    created = WorkFarm(
        owner_ip=ip,
        owner_name='익명 농부',
        money=rules.START_MONEY,
        plots=[None] * rules.START_PLOTS,
        buildings={},
    )
    session.add(created)
    try:
        await session.commit()
    except IntegrityError:
        # 탭 두 개를 동시에 열면 여기로 온다 — 먼저 만들어진 걸 쓴다
        await session.rollback()
        return await session.scalar(select(WorkFarm).where(_by_ip(ip)))
    await session.refresh(created)
    return created


async def _respond(session: AsyncSession, farm: WorkFarm, **extra) -> JSONResponse:
    await session.commit()
    await session.refresh(farm)
    return JSONResponse({**rules.state_view(farm), **extra})


async def _body(request: Request) -> dict:
    try:
        data = await request.json()
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


@router.get('/')
async def api_state(request: Request, session: AsyncSession = Depends(get_session)):
    farm = await _get_or_create(request, session)
    return JSONResponse(rules.state_view(farm))


@router.post('/name/')
async def api_name(request: Request, session: AsyncSession = Depends(get_session)):
    farm = await _get_or_create(request, session)
    data = await _body(request)
    farm.owner_name = (data.get('name') or '익명 농부').strip()[:32] or '익명 농부'
    return await _respond(session, farm)


@router.post('/plant/')
async def api_plant(request: Request, session: AsyncSession = Depends(get_session)):
    farm = await _get_or_create(request, session)
    data = await _body(request)
    try:
        rules.plant(farm, int(data.get('plot', -1)), str(data.get('crop', '')))
    except (rules.FarmError, ValueError, TypeError) as e:
        return JSONResponse({'error': str(e) or '잘못된 요청입니다.'}, status_code=400)
    return await _respond(session, farm)


@router.post('/harvest/')
async def api_harvest(request: Request, session: AsyncSession = Depends(get_session)):
    farm = await _get_or_create(request, session)
    data = await _body(request)
    try:
        earned = rules.harvest(farm, int(data.get('plot', -1)))
    except (rules.FarmError, ValueError, TypeError) as e:
        return JSONResponse({'error': str(e) or '잘못된 요청입니다.'}, status_code=400)
    return await _respond(session, farm, earned=earned)


@router.post('/harvest-all/')
async def api_harvest_all(request: Request, session: AsyncSession = Depends(get_session)):
    farm = await _get_or_create(request, session)
    try:
        picked, earned = rules.harvest_all(farm)
    except rules.FarmError as e:
        return JSONResponse({'error': str(e)}, status_code=400)
    return await _respond(session, farm, earned=earned, picked=picked)


@router.post('/plant-all/')
async def api_plant_all(request: Request, session: AsyncSession = Depends(get_session)):
    farm = await _get_or_create(request, session)
    data = await _body(request)
    try:
        planted, spent = rules.plant_all(farm, str(data.get('crop', '')))
    except rules.FarmError as e:
        return JSONResponse({'error': str(e)}, status_code=400)
    return await _respond(session, farm, planted=planted, spent=spent)


@router.post('/buy/')
async def api_buy(request: Request, session: AsyncSession = Depends(get_session)):
    farm = await _get_or_create(request, session)
    data = await _body(request)
    try:
        cost = rules.buy(farm, str(data.get('item', '')))
    except rules.FarmError as e:
        return JSONResponse({'error': str(e)}, status_code=400)
    return await _respond(session, farm, spent=cost)


# ---------------------------------------------------------------- 공용 저장 슬롯

MAX_SAVE_BYTES = 64 * 1024
SAVE_GAMES = {'stardew'}


@router.get('/save/{game}/')
async def api_save_load(game: str, request: Request, session: AsyncSession = Depends(get_session)):
    if game not in SAVE_GAMES:
        return JSONResponse({'error': '그런 게임이 없습니다.'}, status_code=404)

    row = await session.scalar(
        select(WorkGameSave).where(
            WorkGameSave.owner_ip == cast(client_ip(request), INET),
            WorkGameSave.game == game,
        )
    )
    return JSONResponse({'data': row.data if row else None})


@router.post('/save/{game}/')
async def api_save_store(game: str, request: Request, session: AsyncSession = Depends(get_session)):
    if game not in SAVE_GAMES:
        return JSONResponse({'error': '그런 게임이 없습니다.'}, status_code=404)

    body = await _body(request)
    data = body.get('data')
    if not isinstance(data, dict):
        return JSONResponse({'error': '잘못된 저장 데이터입니다.'}, status_code=400)
    if len(json.dumps(data)) > MAX_SAVE_BYTES:
        return JSONResponse({'error': '저장 데이터가 너무 큽니다.'}, status_code=400)

    ip = client_ip(request)
    row = await session.scalar(
        select(WorkGameSave).where(
            WorkGameSave.owner_ip == cast(ip, INET),
            WorkGameSave.game == game,
        )
    )
    if row:
        row.data = data
    else:
        session.add(WorkGameSave(owner_ip=ip, game=game, data=data))

    try:
        await session.commit()
    except IntegrityError:
        # 탭을 두 개 열어 동시에 저장하면 여기로 온다 — 한 번 더 시도한다
        await session.rollback()
        again = await session.scalar(
            select(WorkGameSave).where(
                WorkGameSave.owner_ip == cast(ip, INET),
                WorkGameSave.game == game,
            )
        )
        if again:
            again.data = data
            await session.commit()
    return JSONResponse({'saved': True})


@router.get('/ranking/')
async def api_ranking(request: Request, session: AsyncSession = Depends(get_session)):
    """부자 순위. 자산은 DB 에 없는 계산값이라 파이썬에서 정렬한다
    (플레이어가 몇 명뿐이라 이걸로 충분하다)."""
    rows = (await session.scalars(
        select(WorkFarm).order_by(desc(WorkFarm.money)).limit(200)
    )).all()

    # asyncpg 는 inet 을 ipaddress 객체로 돌려주므로 문자열과 직접 비교하면 안 된다
    me = client_ip(request)
    ranked = sorted(
        (
            {
                'name': f.owner_name,
                'net_worth': rules.net_worth(f.money, f.buildings or {}),
                'money': f.money,
                'mine': str(f.owner_ip) == str(me),
            }
            for f in rows
        ),
        key=lambda r: r['net_worth'],
        reverse=True,
    )
    return JSONResponse({'ranking': ranked[:RANKING_LIMIT]})
