/* 픽셀아트를 코드로 그린다 — 이미지 파일을 저장소에 두지 않기 위해서.

   각 스프라이트는 문자 격자 + 팔레트로 정의하고, 처음 한 번 오프스크린 캔버스에
   구워둔 뒤 그 캔버스를 복사해 쓴다 (매 프레임 픽셀을 찍으면 느리다).
   '.' 은 투명. */

export const TILE = 16;          // 원본 픽셀 크기. 화면에는 정수배로 확대해 그린다.

const PALETTE = {
    // 땅
    g: '#5c9e3f', G: '#4a8533', h: '#6fb04a',   // 잔디
    d: '#8b6239', D: '#704e2c', e: '#a3764a',   // 흙
    w: '#3f6fa8', W: '#5b8cc4',                 // 물
    s: '#c2b280', S: '#a89768',                 // 모래/길
    // 사람
    k: '#2b2b2b', f: '#f0c090', F: '#d9a878',   // 선/피부
    b: '#3a6ea5', B: '#2c5480',                 // 옷
    r: '#a33b3b', y: '#e8c34a',
    // 작물
    n: '#3d7a2e', N: '#2c5c22',                 // 줄기
    o: '#e07a3c', p: '#d94f6a', u: '#8e5bb5',
    v: '#f2e14c', c: '#e8e8e8',
    // 구조물
    t: '#7a4a2b', T: '#5c3720',                 // 나무
    q: '#9aa4ad', Q: '#6f7880',                 // 돌/지붕
    z: '#c9553f',                               // 지붕 빨강
    i: '#ffffff',
};

const SPRITES = {
    grass: [
        'gggggggggggggggg',
        'ggghgggggggggggg',
        'gggggggggggghggg',
        'gggggggggggggggg',
        'gghggggggggggggg',
        'gggggggggggggggg',
        'ggggggggghgggggg',
        'gggggggggggggggg',
        'gggggggggggggggg',
        'ggggghgggggggggg',
        'gggggggggggggggg',
        'ggggggggggggghgg',
        'gggggggggggggggg',
        'ghgggggggggggggg',
        'gggggggggggggggg',
        'ggggggggggggggGg',
    ],
    soil: [
        'dddddddddddddddd',
        'dDdddddddddDdddd',
        'dddddddDdddddddd',
        'ddddDddddddddddd',
        'ddddddddddddDddd',
        'ddDdddddddddddDd',
        'dddddddddDdddddd',
        'dddddDdddddddddd',
        'ddddddddddddddDd',
        'dDddddddddDddddd',
        'ddddddDddddddddd',
        'dddddddddddDdddd',
        'ddDddddddddddddd',
        'ddddddddDddddddd',
        'ddddDddddddddDdd',
        'dddddddddddddddd',
    ],
    tilled: [
        'DDDDDDDDDDDDDDDD',
        'dddddddddddddddd',
        'eeeeeeeeeeeeeeee',
        'dddddddddddddddd',
        'DDDDDDDDDDDDDDDD',
        'dddddddddddddddd',
        'eeeeeeeeeeeeeeee',
        'dddddddddddddddd',
        'DDDDDDDDDDDDDDDD',
        'dddddddddddddddd',
        'eeeeeeeeeeeeeeee',
        'dddddddddddddddd',
        'DDDDDDDDDDDDDDDD',
        'dddddddddddddddd',
        'eeeeeeeeeeeeeeee',
        'dddddddddddddddd',
    ],
    watered: [
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
        'DDDDDDDDDDDDDDDD',
    ],
    water: [
        'wwwwwwwwwwwwwwww',
        'wwwWwwwwwwwwwwww',
        'wwwwwwwwwWwwwwww',
        'wwwwwwwwwwwwwwww',
        'wWwwwwwwwwwwwWww',
        'wwwwwwwwwwwwwwww',
        'wwwwwwwWwwwwwwww',
        'wwwwwwwwwwwwwwww',
        'wwwwWwwwwwwwwwww',
        'wwwwwwwwwwwWwwww',
        'wwwwwwwwwwwwwwww',
        'wwWwwwwwwwwwwwww',
        'wwwwwwwwwWwwwwww',
        'wwwwwwwwwwwwwwww',
        'wwwwwwWwwwwwwwww',
        'wwwwwwwwwwwwwwww',
    ],
    path: [
        'ssssssssssssssss',
        'sSssssssSsssssss',
        'ssssssssssssssss',
        'sssSsssssssssSss',
        'ssssssssssssssss',
        'ssssssSsssssssss',
        'ssssssssssssssss',
        'sSsssssssssSssss',
        'ssssssssssssssss',
        'ssssSsssssssssss',
        'ssssssssssSsssss',
        'ssssssssssssssss',
        'sssssssSssssssss',
        'ssssssssssssssss',
        'sSsssssssssssSss',
        'ssssssssssssssss',
    ],
    tree: [
        '......nn........',
        '....nnNNnn......',
        '...nNNNNNNn.....',
        '..nNNnNNnNNn....',
        '.nNNNNNNNNNNn...',
        '.nNNnNNNNnNNn...',
        'nNNNNNNNNNNNNn..',
        'nNNnNNNNNNnNNn..',
        '.nNNNNNNNNNNn...',
        '..nNNNNNNNNn....',
        '....nnNNnn......',
        '......tt........',
        '......tT........',
        '......tT........',
        '.....ttTT.......',
        '....TTTTTT......',
    ],
    house: [
        '.....zzzzzz.....',
        '....zzzzzzzz....',
        '...zzzzzzzzzz...',
        '..zzzzzzzzzzzz..',
        '.zzzzzzzzzzzzzz.',
        'zzzzzzzzzzzzzzzz',
        'tttttttttttttttt',
        'tTttttttttttttTt',
        'tttttiiiitttttt.',
        'ttttti..ittttt..',
        'tTtttiiiittttTt.',
        'tttttttttttttt..',
        'ttttttkkkttttt..',
        'tTtttTk.ktttTt..',
        'tttttTkkkttttt..',
        'TTTTTTTTTTTTTTTT',
    ],
    shop: [
        '.....QQQQQQ.....',
        '....QQQQQQQQ....',
        '...QQQQQQQQQQ...',
        '..QQQQQQQQQQQQ..',
        '.QQQQQQQQQQQQQQ.',
        'QQQQQQQQQQQQQQQQ',
        'ssssssssssssssss',
        'sSssyyyyyyyysssS',
        'ssssyvvvvvvysss.',
        'sSssyvvvvvvysss.',
        'ssssyyyyyyyysss.',
        'ssssssssssssss..',
        'ssssssTTTsssss..',
        'sSsssTk.kTssSs..',
        'sssssTTTTsssss..',
        'SSSSSSSSSSSSSSSS',
    ],
    bed: [
        '.tttttttttttttt.',
        '.tiiiiiiiiiiiit.',
        '.tiiiiiiiiiiiit.',
        '.tirrrrrrrrrrit.',
        '.tirrrrrrrrrrit.',
        '.tirrrrrrrrrrit.',
        '.tirrrrrrrrrrit.',
        '.tirrrrrrrrrrit.',
        '.tirrrrrrrrrrit.',
        '.tirrrrrrrrrrit.',
        '.tiiiiiiiiiiiit.',
        '.tiiiiiiiiiiiit.',
        '.tttttttttttttt.',
        '.T............T.',
        '.T............T.',
        '................',
    ],
    fence: [
        '................',
        '................',
        'tttttttttttttttt',
        'TTTTTTTTTTTTTTTT',
        '...tt......tt...',
        '...tt......tt...',
        'tttttttttttttttt',
        'TTTTTTTTTTTTTTTT',
        '...tt......tt...',
        '...tt......tt...',
        '...tt......tt...',
        '...tt......tt...',
        '...TT......TT...',
        '................',
        '................',
        '................',
    ],
};

/* 작물 4단계 — 씨앗 / 새싹 / 자람 / 수확기.
   마지막 단계는 열매 색만 바뀌므로 repeat() 로 조립한다 (손으로 세면 틀린다). */
const dot = (n) => '.'.repeat(n);

function cropStages(F) {
    return [
        [
            '................', '................', '................', '................',
            '................', '................', '................', '................',
            '................', '................', '.......n........', '................',
            '................', '................', '................', '................',
        ],
        [
            '................', '................', '................', '................',
            '................', '................', '................', '.......n........',
            '......nNn.......', '.......n........', '.......n........', '................',
            '................', '................', '................', '................',
        ],
        [
            '................', '................', '................', '................',
            '.....n...n......', '......nNn.......', '.....nNNNn......', '......nNn.......',
            '.......n........', '.....n.n.n......', '......nnn.......', '.......n........',
            '.......n........', '................', '................', '................',
        ],
        [
            '................',
            '................',
            '.....n....n.....',
            `${dot(4)}n${F.repeat(6)}n${dot(4)}`,
            `${dot(3)}${F.repeat(10)}${dot(3)}`,
            `${dot(3)}${F.repeat(10)}${dot(3)}`,
            `${dot(4)}${F.repeat(8)}${dot(4)}`,
            '.....nnnnnn.....',
            '.......nn.......',
            '......n..n......',
            '.......nn.......',
            '.......nn.......',
            '................',
            '................',
            '................',
            '................',
        ],
    ];
}

/* 4방향 × 2프레임 캐릭터 */
function playerFrames() {
    const base = {
        down: [
            '.....kkkkkk.....', '....kffffffk....', '...kffffffffk...', '...kfkffffkfk...',
            '...kffffffffk...', '...kfffkkfffk...', '....kffffffk....', '.....kkkkkk.....',
            '...bbbbbbbbbb...', '..bbBbbbbbBbbb..', '..bbbbbbbbbbbb..', '..bbbbbbbbbbbb..',
            '...bbbbbbbbbb...', '....kk....kk....', '....kk....kk....', '...kkk....kkk...',
        ],
        up: [
            '.....kkkkkk.....', '....kFFFFFFk....', '...kFFFFFFFFk...', '...kFFFFFFFFk...',
            '...kFFFFFFFFk...', '...kFFFFFFFFk...', '....kFFFFFFk....', '.....kkkkkk.....',
            '...bbbbbbbbbb...', '..bbBbbbbbBbbb..', '..bbbbbbbbbbbb..', '..bbbbbbbbbbbb..',
            '...bbbbbbbbbb...', '....kk....kk....', '....kk....kk....', '...kkk....kkk...',
        ],
        right: [
            '.....kkkkkk.....', '....kffffffk....', '...kffffffffk...', '...kffffkfkk....',
            '...kffffffffk...', '...kfffffkkk....', '....kffffffk....', '.....kkkkkk.....',
            '....bbbbbbbb....', '...bbbbbbbbBb...', '...bbbbbbbbbb...', '...bbbbbbbbbb...',
            '....bbbbbbbb....', '.....kk..kk.....', '.....kk..kk.....', '....kkk..kkk....',
        ],
    };
    base.left = base.right.map((row) => row.split('').reverse().join(''));

    // 걷는 프레임 — 다리만 어긋나게
    const step = (rows) => rows.map((row, i) => {
        if (i < 13) return row;
        return row.split('').reverse().join('');
    });

    const out = {};
    Object.entries(base).forEach(([dir, rows]) => {
        out[dir] = [rows, step(rows)];
    });
    return out;
}

/* ---------------- 굽기 ---------------- */

const cache = new Map();

function bake(rows) {
    const c = document.createElement('canvas');
    c.width = TILE;
    c.height = TILE;
    const g = c.getContext('2d');
    rows.forEach((row, y) => {
        for (let x = 0; x < TILE; x += 1) {
            const ch = row[x];
            if (!ch || ch === '.') continue;
            const color = PALETTE[ch];
            if (!color) continue;
            g.fillStyle = color;
            g.fillRect(x, y, 1, 1);
        }
    });
    return c;
}

function put(key, rows) {
    cache.set(key, bake(rows));
}

let ready = false;

export function initArt() {
    if (ready) return;

    Object.entries(SPRITES).forEach(([k, rows]) => put(k, rows));

    // 작물 — 종류별 색만 다르다
    const fruit = { parsnip: 'v', potato: 'o', tomato: 'p', eggplant: 'u', melon: 'c' };
    Object.entries(fruit).forEach(([crop, color]) => {
        cropStages(color).forEach((rows, i) => put(`crop_${crop}_${i}`, rows));
    });

    const frames = playerFrames();
    Object.entries(frames).forEach(([dir, list]) => {
        list.forEach((rows, i) => put(`player_${dir}_${i}`, rows));
    });

    ready = true;
}

export function sprite(key) {
    return cache.get(key) || null;
}
