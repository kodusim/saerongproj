/* 맵과 규칙 데이터.

   맵은 문자 격자로 손으로 그렸다.
     . 잔디   , 흙(밭 만들 수 있는 곳)   ~ 물   # 길
     T 나무   H 집   S 상점   B 침대     F 울타리
   대문자 지형은 전부 못 지나간다 (물 포함). */

export const MAP = [
    'FFFFFFFFFFFFFFFFFFFF',
    'F..T.....##.....T..F',
    'F........##........F',
    'F..,,,,..##..,,,,..F',
    'F..,,,,..##..,,,,..F',
    'F..,,,,..##..,,,,..F',
    'F..,,,,..##..,,,,..F',
    'F........##........F',
    'F~~~.....##.....H..F',
    'F~~~.....##........F',
    'F~~~.....##....B...F',
    'F........##........F',
    'F..,,,,..##..S.....F',
    'F..,,,,..##........F',
    'F..T.....##.....T..F',
    'FFFFFFFFFFFFFFFFFFFF',
];

export const COLS = MAP[0].length;
export const ROWS = MAP.length;

const SOLID = new Set(['F', 'T', 'H', 'S', '~']);

export function tileAt(x, y) {
    if (y < 0 || y >= ROWS || x < 0 || x >= COLS) return 'F';
    return MAP[y][x];
}

export function isSolid(x, y) {
    return SOLID.has(tileAt(x, y));
}

/** 물을 뜰 수 있는 칸인지 (물 옆에 서 있으면 된다) */
export function isWater(x, y) {
    return tileAt(x, y) === '~';
}

export function isTillable(x, y) {
    return tileAt(x, y) === ',';
}

/* ---------------- 작물 ---------------- */

export const CROPS = {
    parsnip:  { name: '파스닙',  seed: 20,  days: 2, sell: 45,  color: '#f2e14c' },
    potato:   { name: '감자',    seed: 50,  days: 3, sell: 120, color: '#e07a3c' },
    tomato:   { name: '토마토',  seed: 110, days: 4, sell: 320, color: '#d94f6a' },
    eggplant: { name: '가지',    seed: 220, days: 5, sell: 750, color: '#8e5bb5' },
    melon:    { name: '멜론',    seed: 500, days: 7, sell: 2200, color: '#e8e8e8' },
};

export const CROP_KEYS = Object.keys(CROPS);

/* ---------------- 도구 업그레이드 ---------------- */

export const UPGRADES = {
    can: {
        name: '물뿌리개 확장',
        desc: '한 번 길으면 더 많이 물을 줍니다 (+6칸)',
        base: 300, growth: 2.0, max: 5,
    },
    boots: {
        name: '좋은 신발',
        desc: '이동이 빨라집니다',
        base: 400, growth: 2.4, max: 3,
    },
    stamina: {
        name: '체력 단련',
        desc: '하루 기운이 +20 늘어납니다',
        base: 500, growth: 2.2, max: 5,
    },
};

export function upgradeCost(key, owned) {
    const u = UPGRADES[key];
    return Math.round(u.base * (u.growth ** owned));
}

/* ---------------- 초기 상태 ---------------- */

export const BASE_ENERGY = 60;
export const BASE_CAN = 12;

export function newState() {
    return {
        day: 1,
        money: 120,
        energy: BASE_ENERGY,
        water: 0,
        seeds: { parsnip: 3 },
        upgrades: { can: 0, boots: 0, stamina: 0 },
        selected: 'parsnip',
        // 밭 상태: 'x,y' → { tilled, watered, crop, stage }
        tiles: {},
        px: 9,
        py: 11,
        dir: 'down',
        shipped: 0,
    };
}

export function maxEnergy(s) {
    return BASE_ENERGY + (s.upgrades.stamina || 0) * 20;
}

export function maxWater(s) {
    return BASE_CAN + (s.upgrades.can || 0) * 6;
}

export function walkSpeed(s) {
    return 4.2 + (s.upgrades.boots || 0) * 1.6;   // 초당 타일
}

/** 하루를 넘긴다 — 물 준 작물만 자란다 */
export function advanceDay(s) {
    let grown = 0;
    let withered = 0;

    Object.entries(s.tiles).forEach(([, t]) => {
        if (t.crop) {
            if (t.watered) {
                const need = CROPS[t.crop].days;
                if (t.stage < need) {
                    t.stage += 1;
                    grown += 1;
                }
            } else {
                // 물을 안 주면 자라지 않는다 (죽지는 않는다 — 너무 가혹해서)
                withered += 1;
            }
        }
        t.watered = false;
    });

    s.day += 1;
    s.energy = maxEnergy(s);
    s.water = 0;
    return { grown, withered };
}

export function tileKey(x, y) {
    return `${x},${y}`;
}

export function cropReady(t) {
    return Boolean(t && t.crop && t.stage >= CROPS[t.crop].days);
}
