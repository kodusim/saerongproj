/* 우리집 농장 2 — 걸어다니며 농사짓는 타일 게임.

   스타듀밸리를 흉내낸 것이지 재현이 아니다. 걷기 / 괭이질 / 심기 / 물주기 /
   수확 / 잠자기 / 상점, 그리고 하루 단위 성장까지가 전부다.

   저장은 서버(work_gamesave)에 통째로 맡긴다. 이동·타일 시뮬레이션을 서버에서
   돌리는 건 현실적이지 않아 **클라이언트를 믿는다** — 혼자 하는 게임이고
   순위가 걸린 쪽(work_workfarm)은 서버가 계산하므로 영향이 없다. */
import { api } from '../../../lib/api.js';
import { initArt, sprite, TILE } from './art.js';
import {
    CROPS, CROP_KEYS, COLS, ROWS, UPGRADES,
    advanceDay, cropReady, isSolid, isTillable, isWater,
    maxEnergy, maxWater, newState, tileAt, tileKey, upgradeCost, walkSpeed,
} from './world.js';

const SCALE = 2;                       // 16px 타일 → 32px
const VIEW_W = COLS * TILE * SCALE;
const VIEW_H = ROWS * TILE * SCALE;
const SAVE_URL = '/work/api/farm/save/stardew/';
const AUTOSAVE_MS = 20000;

export default {
    id: 'stardew',
    name: '우리집 농장 2',
    icon: '🌾',
    desc: '걸어다니며 짓는 농사 (WASD)',
    persistent: true,

    create(ctx) {
        let el = null;
        let cv = null;
        let g = null;
        let raf = null;
        let saveTimer = null;
        let dead = false;

        let s = newState();
        let loaded = false;
        let shopOpen = false;
        let toast = '';
        let toastUntil = 0;
        let lastTs = 0;
        let animT = 0;
        let dirty = false;

        const keys = new Set();

        /* ---------------- 저장 ---------------- */

        async function load() {
            const { ok, data } = await api.get(SAVE_URL);
            if (dead) return;
            if (ok && data && data.data) {
                s = { ...newState(), ...data.data };
                s.upgrades = { can: 0, boots: 0, stamina: 0, ...(s.upgrades || {}) };
                s.seeds = s.seeds || {};
                s.tiles = s.tiles || {};
            }
            loaded = true;
        }

        async function save() {
            if (!loaded || dead) return;
            dirty = false;
            await api.postJSON(SAVE_URL, { data: s });
        }

        /* ---------------- 알림 ---------------- */

        function say(msg) {
            toast = msg;
            toastUntil = performance.now() + 1800;
        }

        /* ---------------- 행동 ---------------- */

        function facingTile() {
            const d = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] }[s.dir];
            return [Math.round(s.px) + d[0], Math.round(s.py) + d[1]];
        }

        function spend(n) {
            if (s.energy < n) {
                say('기운이 없습니다. 침대에서 자세요.');
                return false;
            }
            s.energy -= n;
            return true;
        }

        function act() {
            if (shopOpen) return;
            const [tx, ty] = facingTile();
            const ch = tileAt(tx, ty);
            const key = tileKey(tx, ty);
            const t = s.tiles[key];

            // 침대 → 잠자기
            if (ch === 'B') {
                sleep();
                return;
            }
            // 상점
            if (ch === 'S') {
                shopOpen = true;
                return;
            }
            // 물 긷기
            if (isWater(tx, ty)) {
                s.water = maxWater(s);
                say(`물을 가득 채웠습니다 (${s.water})`);
                dirty = true;
                return;
            }
            if (!isTillable(tx, ty)) {
                say('여기서는 할 게 없습니다.');
                return;
            }

            // 수확
            if (cropReady(t)) {
                const crop = CROPS[t.crop];
                s.money += crop.sell;
                s.shipped += 1;
                delete s.tiles[key];
                say(`${crop.name} 수확! +${crop.sell}원`);
                dirty = true;
                return;
            }
            // 물주기
            if (t && t.crop && !t.watered) {
                if (s.water <= 0) {
                    say('물이 없습니다. 연못에서 길어오세요.');
                    return;
                }
                if (!spend(1)) return;
                s.water -= 1;
                t.watered = true;
                dirty = true;
                return;
            }
            // 심기
            if (t && t.tilled && !t.crop) {
                const sel = s.selected;
                if (!s.seeds[sel]) {
                    say(`${CROPS[sel].name} 씨앗이 없습니다.`);
                    return;
                }
                if (!spend(1)) return;
                s.seeds[sel] -= 1;
                if (!s.seeds[sel]) delete s.seeds[sel];
                t.crop = sel;
                t.stage = 0;
                dirty = true;
                return;
            }
            // 괭이질
            if (!t) {
                if (!spend(2)) return;
                s.tiles[key] = { tilled: true, watered: false, crop: null, stage: 0 };
                dirty = true;
                return;
            }
            if (t.crop && t.watered) say('이미 물을 줬습니다.');
        }

        function sleep() {
            const { grown } = advanceDay(s);
            say(`${s.day}일차 아침 — 작물 ${grown}칸이 자랐습니다`);
            dirty = true;
            save();
        }

        /* ---------------- 상점 ---------------- */

        function buySeed(k) {
            const c = CROPS[k];
            if (s.money < c.seed) {
                say('돈이 부족합니다.');
                return;
            }
            s.money -= c.seed;
            s.seeds[k] = (s.seeds[k] || 0) + 1;
            s.selected = k;
            dirty = true;
        }

        function buyUpgrade(k) {
            const owned = s.upgrades[k] || 0;
            if (owned >= UPGRADES[k].max) {
                say('더 살 수 없습니다.');
                return;
            }
            const cost = upgradeCost(k, owned);
            if (s.money < cost) {
                say('돈이 부족합니다.');
                return;
            }
            s.money -= cost;
            s.upgrades[k] = owned + 1;
            if (k === 'stamina') s.energy = Math.min(maxEnergy(s), s.energy + 20);
            dirty = true;
        }

        /* ---------------- 이동 ---------------- */

        function move(dt) {
            if (shopOpen) return;
            let dx = 0;
            let dy = 0;
            if (keys.has('a') || keys.has('arrowleft')) dx -= 1;
            if (keys.has('d') || keys.has('arrowright')) dx += 1;
            if (keys.has('w') || keys.has('arrowup')) dy -= 1;
            if (keys.has('s') || keys.has('arrowdown')) dy += 1;

            if (dx) s.dir = dx < 0 ? 'left' : 'right';
            else if (dy) s.dir = dy < 0 ? 'up' : 'down';

            if (!dx && !dy) {
                animT = 0;
                return;
            }
            animT += dt;

            const sp = walkSpeed(s) * dt;
            const len = Math.hypot(dx, dy) || 1;
            const nx = s.px + (dx / len) * sp;
            const ny = s.py + (dy / len) * sp;

            // 축별로 따로 판정해서 벽에 붙어도 미끄러지게
            if (!isSolid(Math.round(nx), Math.round(s.py))) s.px = nx;
            if (!isSolid(Math.round(s.px), Math.round(ny))) s.py = ny;

            s.px = Math.max(1, Math.min(COLS - 2, s.px));
            s.py = Math.max(1, Math.min(ROWS - 2, s.py));
            dirty = true;
        }

        /* ---------------- 그리기 ---------------- */

        function drawSprite(key, x, y) {
            const img = sprite(key);
            if (img) g.drawImage(img, Math.round(x), Math.round(y), TILE * SCALE, TILE * SCALE);
        }

        function draw() {
            g.imageSmoothingEnabled = false;

            for (let y = 0; y < ROWS; y += 1) {
                for (let x = 0; x < COLS; x += 1) {
                    const ch = MAPCHAR(x, y);
                    const px = x * TILE * SCALE;
                    const py = y * TILE * SCALE;

                    // 바닥
                    if (ch === '~') drawSprite('water', px, py);
                    else if (ch === '#') drawSprite('path', px, py);
                    else if (ch === ',') drawSprite('soil', px, py);
                    else drawSprite('grass', px, py);

                    // 밭 상태
                    const t = s.tiles[tileKey(x, y)];
                    if (t && t.tilled) {
                        drawSprite(t.watered ? 'watered' : 'tilled', px, py);
                        if (t.crop) {
                            const stage = Math.min(3, Math.round((t.stage / CROPS[t.crop].days) * 3));
                            drawSprite(`crop_${t.crop}_${stage}`, px, py);
                        }
                    }

                    // 구조물
                    if (ch === 'T') drawSprite('tree', px, py);
                    else if (ch === 'H') drawSprite('house', px, py);
                    else if (ch === 'S') drawSprite('shop', px, py);
                    else if (ch === 'B') drawSprite('bed', px, py);
                    else if (ch === 'F') drawSprite('fence', px, py);
                }
            }

            // 바라보는 칸 표시
            const [fx, fy] = facingTile();
            if (isTillable(fx, fy) || tileAt(fx, fy) === 'B' || tileAt(fx, fy) === 'S' || isWater(fx, fy)) {
                g.strokeStyle = 'rgba(255,255,255,.75)';
                g.lineWidth = 2;
                g.strokeRect(fx * TILE * SCALE + 1, fy * TILE * SCALE + 1,
                    TILE * SCALE - 2, TILE * SCALE - 2);
            }

            // 캐릭터
            const frame = animT > 0 ? (Math.floor(animT * 8) % 2) : 0;
            drawSprite(`player_${s.dir}_${frame}`, s.px * TILE * SCALE, s.py * TILE * SCALE);

            drawHud();
            if (shopOpen) drawShop();
            if (toast && performance.now() < toastUntil) drawToast();
        }

        function drawHud() {
            g.fillStyle = 'rgba(0,0,0,.55)';
            g.fillRect(0, 0, VIEW_W, 26);
            g.fillStyle = '#fff';
            g.font = 'bold 13px "Malgun Gothic", sans-serif';
            g.textBaseline = 'middle';

            const sel = CROPS[s.selected];
            const have = s.seeds[s.selected] || 0;
            g.fillText(
                `${s.day}일차   💰 ${s.money.toLocaleString()}원   `
                + `⚡ ${s.energy}/${maxEnergy(s)}   💧 ${s.water}/${maxWater(s)}   `
                + `🌱 ${sel.name} ×${have}`,
                10, 14,
            );
        }

        function drawToast() {
            g.font = 'bold 13px "Malgun Gothic", sans-serif';
            const w = g.measureText(toast).width + 24;
            const x = (VIEW_W - w) / 2;
            g.fillStyle = 'rgba(0,0,0,.75)';
            g.fillRect(x, VIEW_H - 46, w, 28);
            g.fillStyle = '#fff';
            g.textAlign = 'center';
            g.fillText(toast, VIEW_W / 2, VIEW_H - 32);
            g.textAlign = 'left';
        }

        function drawShop() {
            g.fillStyle = 'rgba(0,0,0,.8)';
            g.fillRect(0, 0, VIEW_W, VIEW_H);

            g.fillStyle = '#fff';
            g.font = 'bold 16px "Malgun Gothic", sans-serif';
            g.fillText('상점  (숫자키로 구매 · ESC 닫기)', 30, 40);

            g.font = '13px "Malgun Gothic", sans-serif';
            let y = 78;
            g.fillText('— 씨앗 —', 30, y);
            y += 24;
            CROP_KEYS.forEach((k, i) => {
                const c = CROPS[k];
                g.fillStyle = s.money >= c.seed ? '#fff' : '#888';
                g.fillText(
                    `${i + 1}. ${c.name}  ${c.seed}원  ·  ${c.days}일  ·  팔면 ${c.sell}원`
                    + `   (보유 ${s.seeds[k] || 0})`,
                    44, y,
                );
                y += 22;
            });

            y += 14;
            g.fillStyle = '#fff';
            g.fillText('— 설비 —', 30, y);
            y += 24;
            Object.entries(UPGRADES).forEach(([k, u], i) => {
                const owned = s.upgrades[k] || 0;
                const full = owned >= u.max;
                const cost = upgradeCost(k, owned);
                g.fillStyle = full ? '#888' : (s.money >= cost ? '#fff' : '#888');
                g.fillText(
                    `${i + 6}. ${u.name} (${owned}/${u.max})  ${full ? '최대' : `${cost.toLocaleString()}원`}`
                    + `   ${u.desc}`,
                    44, y,
                );
                y += 22;
            });
        }

        // 맵 문자 조회를 draw 안에서 쓰기 좋게
        function MAPCHAR(x, y) {
            return tileAt(x, y);
        }

        /* ---------------- 루프 ---------------- */

        function loop(ts) {
            if (dead) return;
            const dt = Math.min(0.05, (ts - lastTs) / 1000 || 0);
            lastTs = ts;
            move(dt);
            draw();
            ctx.setScore(s.money);
            raf = requestAnimationFrame(loop);
        }

        /* ---------------- 입력 ---------------- */

        function onKeyDown(e) {
            const k = e.key.toLowerCase();

            if (shopOpen) {
                if (k === 'escape') { shopOpen = false; e.preventDefault(); return; }
                const n = Number(k);
                if (n >= 1 && n <= CROP_KEYS.length) { buySeed(CROP_KEYS[n - 1]); e.preventDefault(); return; }
                const ups = Object.keys(UPGRADES);
                if (n >= 6 && n < 6 + ups.length) { buyUpgrade(ups[n - 6]); e.preventDefault(); }
                return;
            }

            if (['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright', ' '].includes(k)) {
                e.preventDefault();
            }
            if (k === ' ' || k === 'e') { act(); return; }
            if (k === 'escape') { shopOpen = false; return; }

            // 1~5 로 씨앗 고르기
            const n = Number(k);
            if (n >= 1 && n <= CROP_KEYS.length) {
                s.selected = CROP_KEYS[n - 1];
                return;
            }
            keys.add(k);
        }

        function onKeyUp(e) {
            keys.delete(e.key.toLowerCase());
        }

        function onBlur() {
            keys.clear();
        }

        return {
            mount(stage) {
                el = stage;
                initArt();

                el.innerHTML = `
                    <div class="sd-wrap">
                        <canvas class="sd-canvas" width="${VIEW_W}" height="${VIEW_H}"></canvas>
                        <div class="sd-help">
                            <b>WASD</b> 이동 · <b>Space</b> 행동(괭이질→심기→물주기→수확) ·
                            <b>1~5</b> 씨앗 선택 · 상점/침대 앞에서 <b>Space</b>
                            <br>물은 왼쪽 <b>연못</b>에서 긷습니다. 물을 준 작물만 다음 날 자랍니다.
                        </div>
                    </div>
                `;
                cv = el.querySelector('.sd-canvas');
                g = cv.getContext('2d');

                document.addEventListener('keydown', onKeyDown);
                document.addEventListener('keyup', onKeyUp);
                window.addEventListener('blur', onBlur);

                ctx.setInfo('밭을 갈고 씨앗을 심고 물을 준 뒤, 침대에서 자면 하루가 갑니다.');

                load().then(() => {
                    if (dead) return;
                    lastTs = performance.now();
                    raf = requestAnimationFrame(loop);
                });

                saveTimer = setInterval(() => { if (dirty) save(); }, AUTOSAVE_MS);
            },
            destroy() {
                dead = true;
                cancelAnimationFrame(raf);
                clearInterval(saveTimer);
                document.removeEventListener('keydown', onKeyDown);
                document.removeEventListener('keyup', onKeyUp);
                window.removeEventListener('blur', onBlur);
                if (loaded && dirty) save();
            },
        };
    },
};
