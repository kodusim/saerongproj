"""농장 게임 규칙 — 서버가 진실의 원천이다.

시간(작물이 다 자랐는지)과 돈 계산을 클라이언트에 맡기면 조작이 너무 쉽다.
프런트는 상태를 받아 그리고 행동만 보낸다.

작물은 접속하지 않은 사이에도 자란다. `planted_at` 만 저장해두고
필요할 때 경과 시간으로 판정하기 때문에 별도 배치 작업이 필요 없다.
"""
from datetime import datetime, timezone

# ---------------------------------------------------------------- 작물

# grow_sec 은 비닐하우스가 없을 때 기준. price 는 창고가 없을 때 기준.
CROPS = {
    'radish':   {'name': '무',     'icon': '🥬', 'cost': 10,   'grow_sec': 20,   'price': 18},
    'potato':   {'name': '감자',   'icon': '🥔', 'cost': 30,   'grow_sec': 60,   'price': 62},
    'corn':     {'name': '옥수수', 'icon': '🌽', 'cost': 90,   'grow_sec': 180,  'price': 200},
    'strawberry': {'name': '딸기', 'icon': '🍓', 'cost': 240,  'grow_sec': 420,  'price': 560},
    'ginseng':  {'name': '인삼',   'icon': '🌿', 'cost': 700,  'grow_sec': 900,  'price': 1750},
    'truffle':  {'name': '트러플', 'icon': '🍄', 'cost': 2200, 'grow_sec': 1800, 'price': 6000},
}

# ---------------------------------------------------------------- 건물

START_PLOTS = 4
MAX_PLOTS = 16
START_MONEY = 50

BUILDINGS = {
    'plot': {
        'name': '밭 확장', 'icon': '🟫',
        'desc': '심을 수 있는 밭이 1칸 늘어납니다',
        'base': 120, 'growth': 1.7, 'max': MAX_PLOTS - START_PLOTS,
    },
    'greenhouse': {
        'name': '비닐하우스', 'icon': '🏠',
        'desc': '모든 작물이 자라는 시간이 12%씩 짧아집니다',
        'base': 400, 'growth': 2.1, 'max': 6,
    },
    'barn': {
        'name': '창고', 'icon': '🏚️',
        'desc': '수확한 작물을 15%씩 비싸게 팝니다',
        'base': 600, 'growth': 2.2, 'max': 6,
    },
    'tractor': {
        'name': '트랙터', 'icon': '🚜',
        'desc': '‘전부 심기 / 전부 수확’ 버튼이 열립니다',
        'base': 1500, 'growth': 3.0, 'max': 1,
    },
}


def building_cost(key: str, owned: int) -> int:
    """다음 한 채의 가격 — 살수록 비싸진다."""
    b = BUILDINGS[key]
    return int(round(b['base'] * (b['growth'] ** owned)))


def grow_seconds(crop_key: str, buildings: dict) -> int:
    """비닐하우스 1채당 12% 단축 (곱연산이라 0 이 되지 않는다)."""
    base = CROPS[crop_key]['grow_sec']
    level = int(buildings.get('greenhouse', 0))
    return max(3, int(round(base * (0.88 ** level))))


def sell_price(crop_key: str, buildings: dict) -> int:
    """창고 1채당 15% 가산."""
    base = CROPS[crop_key]['price']
    level = int(buildings.get('barn', 0))
    return int(round(base * (1.15 ** level)))


def plot_count(buildings: dict) -> int:
    return min(MAX_PLOTS, START_PLOTS + int(buildings.get('plot', 0)))


def net_worth(money: int, buildings: dict) -> int:
    """부자 순위 기준 — 현금 + 지금까지 건물에 넣은 돈."""
    spent = 0
    for key, owned in (buildings or {}).items():
        if key not in BUILDINGS:
            continue
        for i in range(int(owned)):
            spent += building_cost(key, i)
    return int(money) + spent


# ---------------------------------------------------------------- 상태 계산

def _now() -> datetime:
    return datetime.now(timezone.utc)


def plot_view(plot: dict | None, buildings: dict) -> dict:
    """저장된 밭 한 칸 → 프런트가 그릴 수 있는 형태."""
    if not plot or not plot.get('crop'):
        return {'state': 'empty'}

    crop_key = plot['crop']
    if crop_key not in CROPS:
        return {'state': 'empty'}

    planted = datetime.fromisoformat(plot['planted_at'])
    need = grow_seconds(crop_key, buildings)
    elapsed = (_now() - planted).total_seconds()
    left = max(0.0, need - elapsed)

    return {
        'state': 'ready' if left <= 0 else 'growing',
        'crop': crop_key,
        'name': CROPS[crop_key]['name'],
        'icon': CROPS[crop_key]['icon'],
        'left_sec': round(left, 1),
        'need_sec': need,
        'price': sell_price(crop_key, buildings),
    }


def catalog(buildings: dict) -> dict:
    """지금 시세 기준의 상점 정보."""
    return {
        'crops': [
            {
                'key': k,
                'name': c['name'],
                'icon': c['icon'],
                'cost': c['cost'],
                'grow_sec': grow_seconds(k, buildings),
                'price': sell_price(k, buildings),
            }
            for k, c in CROPS.items()
        ],
        'buildings': [
            {
                'key': k,
                'name': b['name'],
                'icon': b['icon'],
                'desc': b['desc'],
                'owned': int((buildings or {}).get(k, 0)),
                'max': b['max'],
                'cost': building_cost(k, int((buildings or {}).get(k, 0))),
            }
            for k, b in BUILDINGS.items()
        ],
    }


def state_view(farm) -> dict:
    """농장 모델 → API 응답."""
    buildings = farm.buildings or {}
    plots = farm.plots or []
    count = plot_count(buildings)

    # 밭 확장을 샀으면 칸을 늘려서 보여준다
    view = [plot_view(plots[i] if i < len(plots) else None, buildings) for i in range(count)]

    return {
        'owner_name': farm.owner_name,
        'money': farm.money,
        'net_worth': net_worth(farm.money, buildings),
        'plots': view,
        'plot_count': count,
        'buildings': {k: int(buildings.get(k, 0)) for k in BUILDINGS},
        'catalog': catalog(buildings),
        'has_tractor': int(buildings.get('tractor', 0)) > 0,
    }


# ---------------------------------------------------------------- 행동

class FarmError(Exception):
    """플레이어에게 그대로 보여줄 수 있는 오류."""


def _normalized_plots(farm) -> list:
    count = plot_count(farm.buildings or {})
    plots = list(farm.plots or [])
    while len(plots) < count:
        plots.append(None)
    return plots[:count]


def plant(farm, index: int, crop_key: str) -> None:
    if crop_key not in CROPS:
        raise FarmError('그런 작물이 없습니다.')

    plots = _normalized_plots(farm)
    if not 0 <= index < len(plots):
        raise FarmError('그런 밭이 없습니다.')
    if plots[index] and plots[index].get('crop'):
        raise FarmError('이미 뭔가 심어져 있습니다.')

    cost = CROPS[crop_key]['cost']
    if farm.money < cost:
        raise FarmError(f'돈이 부족합니다. ({cost}원 필요)')

    farm.money -= cost
    plots[index] = {'crop': crop_key, 'planted_at': _now().isoformat()}
    farm.plots = plots


def harvest(farm, index: int) -> int:
    plots = _normalized_plots(farm)
    if not 0 <= index < len(plots):
        raise FarmError('그런 밭이 없습니다.')

    buildings = farm.buildings or {}
    view = plot_view(plots[index], buildings)
    if view['state'] != 'ready':
        raise FarmError('아직 다 자라지 않았습니다.')

    earned = view['price']
    farm.money += earned
    plots[index] = None
    farm.plots = plots
    return earned


def harvest_all(farm) -> tuple[int, int]:
    """트랙터 전용. (수확한 칸 수, 번 돈)"""
    buildings = farm.buildings or {}
    if int(buildings.get('tractor', 0)) < 1:
        raise FarmError('트랙터가 있어야 합니다.')

    plots = _normalized_plots(farm)
    earned = 0
    picked = 0
    for i, p in enumerate(plots):
        if plot_view(p, buildings)['state'] == 'ready':
            earned += sell_price(p['crop'], buildings)
            plots[i] = None
            picked += 1

    if not picked:
        raise FarmError('수확할 게 없습니다.')

    farm.money += earned
    farm.plots = plots
    return picked, earned


def plant_all(farm, crop_key: str) -> tuple[int, int]:
    """트랙터 전용. (심은 칸 수, 쓴 돈)"""
    buildings = farm.buildings or {}
    if int(buildings.get('tractor', 0)) < 1:
        raise FarmError('트랙터가 있어야 합니다.')
    if crop_key not in CROPS:
        raise FarmError('그런 작물이 없습니다.')

    cost = CROPS[crop_key]['cost']
    plots = _normalized_plots(farm)
    planted = 0
    spent = 0
    for i, p in enumerate(plots):
        if p and p.get('crop'):
            continue
        if farm.money - spent < cost:
            break
        plots[i] = {'crop': crop_key, 'planted_at': _now().isoformat()}
        spent += cost
        planted += 1

    if not planted:
        raise FarmError('심을 빈 밭이 없거나 돈이 부족합니다.')

    farm.money -= spent
    farm.plots = plots
    return planted, spent


def buy(farm, key: str) -> int:
    if key not in BUILDINGS:
        raise FarmError('그런 건물이 없습니다.')

    buildings = dict(farm.buildings or {})
    owned = int(buildings.get(key, 0))
    if owned >= BUILDINGS[key]['max']:
        raise FarmError('더 살 수 없습니다.')

    cost = building_cost(key, owned)
    if farm.money < cost:
        raise FarmError(f'돈이 부족합니다. ({cost:,}원 필요)')

    farm.money -= cost
    buildings[key] = owned + 1
    farm.buildings = buildings

    if key == 'plot':
        farm.plots = _normalized_plots(farm)
    return cost
