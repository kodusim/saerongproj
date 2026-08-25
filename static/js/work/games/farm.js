/* 농장 — 농사지어 돈 벌고 건물 사서 부자 되기.

   앞의 4개와 달리 **서버에 저장**된다. 작물은 접속하지 않은 사이에도 자라고,
   돈·시간 계산은 전부 서버(app/services/farm.py)가 한다. 여기서는 상태를 받아
   그리고 행동만 보낸다.

   남은 시간은 서버가 준 left_sec 을 화면에서만 깎아 보여주고,
   주기적으로 다시 받아 어긋난 걸 맞춘다. */
import { api } from '../../lib/api.js';
import { getNickname } from '../state.js';

const TICK_MS = 200;
const RESYNC_MS = 15000;

const fmt = (n) => Number(n || 0).toLocaleString();

function timeText(sec) {
    const s = Math.max(0, Math.ceil(sec));
    if (s < 60) return `${s}초`;
    const m = Math.floor(s / 60);
    return s % 60 ? `${m}분 ${s % 60}초` : `${m}분`;
}

export default {
    id: 'farm',
    name: '우리집 농장',
    icon: '🚜',
    desc: '농사지어 부자 되기 (서버 저장)',
    persistent: true,

    create(ctx) {
        let el = null;
        let state = null;
        let ranking = null;
        let tab = 'field';          // 'field' | 'shop' | 'rank'
        let seed = 'radish';        // 선택해 둔 씨앗
        let tickTimer = null;
        let syncTimer = null;
        let flash = '';
        let dead = false;

        /* ---------------- 서버 ---------------- */

        async function pull() {
            const { ok, data } = await api.get('/work/api/farm/');
            if (!ok || !data || dead) return;
            state = data;
            paint();
        }

        async function act(path, body) {
            const { ok, data } = await api.postJSON(`/work/api/farm/${path}`, body || {});
            if (dead) return;
            if (!ok) {
                flash = (data && data.error) || '실패했습니다.';
                paint();
                return;
            }
            state = data;
            if (data.earned) flash = `+${fmt(data.earned)}원`;
            else if (data.spent) flash = `-${fmt(data.spent)}원`;
            else flash = '';
            paint();
        }

        async function pullRanking() {
            const { ok, data } = await api.get('/work/api/farm/ranking/');
            if (!ok || !data || dead) return;
            ranking = data.ranking || [];
            paint();
        }

        /* ---------------- 그리기 ---------------- */

        function header() {
            return `
                <div class="fm-top">
                    <span class="fm-money">💰 ${fmt(state.money)}원</span>
                    <span class="fm-worth">자산 ${fmt(state.net_worth)}원</span>
                    ${flash ? `<span class="fm-flash">${flash}</span>` : ''}
                    <span class="gm-spacer"></span>
                    <span class="fm-owner">${state.owner_name}</span>
                    <button class="gm-btn" type="button" data-farm="rename">이름</button>
                </div>
                <div class="fm-tabs">
                    <button class="fm-tab${tab === 'field' ? ' on' : ''}" type="button" data-tab="field">밭</button>
                    <button class="fm-tab${tab === 'shop' ? ' on' : ''}" type="button" data-tab="shop">상점</button>
                    <button class="fm-tab${tab === 'rank' ? ' on' : ''}" type="button" data-tab="rank">부자 순위</button>
                </div>
            `;
        }

        function seedBar() {
            const crops = state.catalog.crops;
            return `
                <div class="fm-seeds">
                    ${crops.map((c) => `
                        <button class="fm-seed${c.key === seed ? ' on' : ''}${state.money < c.cost ? ' poor' : ''}"
                                type="button" data-seed="${c.key}"
                                title="${c.name} · ${fmt(c.cost)}원 · ${timeText(c.grow_sec)} · 팔면 ${fmt(c.price)}원">
                            <span class="fm-seed-ic">${c.icon}</span>
                            <span class="fm-seed-n">${c.name}</span>
                            <span class="fm-seed-c">${fmt(c.cost)}원</span>
                        </button>
                    `).join('')}
                </div>
                ${state.has_tractor ? `
                    <div class="fm-tractor">
                        <button class="gm-btn" type="button" data-farm="plant-all">🚜 전부 심기</button>
                        <button class="gm-btn primary" type="button" data-farm="harvest-all">🚜 전부 수확</button>
                    </div>
                ` : ''}
            `;
        }

        function plotCell(p, i) {
            if (p.state === 'empty') {
                return `<button class="fm-plot empty" type="button" data-plant="${i}">
                            <span class="fm-plot-ic">🟫</span>
                            <span class="fm-plot-t">비어 있음</span>
                        </button>`;
            }
            if (p.state === 'ready') {
                return `<button class="fm-plot ready" type="button" data-harvest="${i}">
                            <span class="fm-plot-ic">${p.icon}</span>
                            <span class="fm-plot-t">수확! +${fmt(p.price)}</span>
                        </button>`;
            }
            const pct = Math.max(0, Math.min(100, (1 - p.left_sec / p.need_sec) * 100));
            return `<div class="fm-plot growing">
                        <span class="fm-plot-ic">🌱</span>
                        <span class="fm-plot-t" data-left="${i}">${timeText(p.left_sec)}</span>
                        <span class="fm-plot-bar"><i style="width:${pct}%"></i></span>
                    </div>`;
        }

        function fieldView() {
            return `
                ${seedBar()}
                <div class="fm-plots">${state.plots.map(plotCell).join('')}</div>
                <div class="fm-hint">
                    씨앗을 고른 뒤 빈 밭을 누르면 심어집니다. 다 자란 밭을 누르면 수확합니다.
                    작물은 창을 닫아도 계속 자랍니다.
                </div>
            `;
        }

        function shopView() {
            const { crops, buildings } = state.catalog;
            return `
                <div class="fm-shop">
                    <div class="fm-shop-title">건물 · 설비</div>
                    ${buildings.map((b) => {
                        const full = b.owned >= b.max;
                        const poor = state.money < b.cost;
                        return `
                            <div class="fm-item">
                                <span class="fm-item-ic">${b.icon}</span>
                                <span class="fm-item-main">
                                    <b>${b.name}</b> <i>${b.owned}/${b.max}</i>
                                    <span class="fm-item-desc">${b.desc}</span>
                                </span>
                                <button class="gm-btn${poor || full ? '' : ' primary'}" type="button"
                                        data-buy="${b.key}" ${full || poor ? 'disabled' : ''}>
                                    ${full ? '최대' : `${fmt(b.cost)}원`}
                                </button>
                            </div>
                        `;
                    }).join('')}

                    <div class="fm-shop-title">작물 시세 (지금 내 농장 기준)</div>
                    <div class="fm-price-head">
                        <span>작물</span><span>씨앗</span><span>자라는 시간</span><span>판매가</span><span>초당</span>
                    </div>
                    ${crops.map((c) => `
                        <div class="fm-price">
                            <span>${c.icon} ${c.name}</span>
                            <span>${fmt(c.cost)}</span>
                            <span>${timeText(c.grow_sec)}</span>
                            <span>${fmt(c.price)}</span>
                            <span class="fm-rate">${((c.price - c.cost) / c.grow_sec).toFixed(1)}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        function rankView() {
            if (!ranking) return '<div class="fm-hint">불러오는 중…</div>';
            if (!ranking.length) return '<div class="fm-hint">아직 농장이 없습니다.</div>';
            return `
                <div class="fm-rank">
                    ${ranking.map((r, i) => `
                        <div class="fm-rank-row${r.mine ? ' mine' : ''}">
                            <span class="fm-rank-no">${i + 1}</span>
                            <span class="fm-rank-name">${r.name}${r.mine ? ' (나)' : ''}</span>
                            <span class="fm-rank-w">${fmt(r.net_worth)}원</span>
                        </div>
                    `).join('')}
                </div>
                <div class="fm-hint">자산 = 현금 + 지금까지 건물에 넣은 돈</div>
            `;
        }

        function paint() {
            if (!state || !el) return;
            ctx.setScore(state.net_worth);
            const body = tab === 'field' ? fieldView() : tab === 'shop' ? shopView() : rankView();
            el.innerHTML = `<div class="fm-wrap">${header()}${body}</div>`;
        }

        /** 남은 시간만 화면에서 깎는다 (매번 다시 그리면 클릭이 튄다) */
        function tick() {
            if (!state || tab !== 'field') return;
            let becameReady = false;
            state.plots.forEach((p, i) => {
                if (p.state !== 'growing') return;
                p.left_sec = Math.max(0, p.left_sec - TICK_MS / 1000);
                if (p.left_sec <= 0) {
                    becameReady = true;
                    return;
                }
                const t = el.querySelector(`[data-left="${i}"]`);
                if (t) t.textContent = timeText(p.left_sec);
                const bar = t && t.parentElement.querySelector('.fm-plot-bar i');
                if (bar) bar.style.width = `${(1 - p.left_sec / p.need_sec) * 100}%`;
            });
            if (becameReady) pull();
        }

        /* ---------------- 입력 ---------------- */

        function onClick(e) {
            const t = e.target.closest('[data-tab],[data-seed],[data-plant],[data-harvest],[data-buy],[data-farm]');
            if (!t) return;

            if (t.dataset.tab) {
                tab = t.dataset.tab;
                flash = '';
                if (tab === 'rank') pullRanking();
                paint();
                return;
            }
            if (t.dataset.seed) {
                seed = t.dataset.seed;
                paint();
                return;
            }
            if (t.dataset.plant !== undefined) {
                act('plant/', { plot: Number(t.dataset.plant), crop: seed });
                return;
            }
            if (t.dataset.harvest !== undefined) {
                act('harvest/', { plot: Number(t.dataset.harvest) });
                return;
            }
            if (t.dataset.buy) {
                act('buy/', { item: t.dataset.buy });
                return;
            }

            const cmd = t.dataset.farm;
            if (cmd === 'harvest-all') act('harvest-all/', {});
            if (cmd === 'plant-all') act('plant-all/', { crop: seed });
            if (cmd === 'rename') {
                const name = prompt('농장 주인 이름', state.owner_name);
                if (name !== null) act('name/', { name: name.trim() });
            }
        }

        return {
            mount(stage) {
                el = stage;
                el.addEventListener('click', onClick);
                ctx.setInfo('농사지어 돈을 벌고, 밭을 넓히고, 건물을 올려 부자가 되세요.');

                pull().then(() => {
                    // 채팅 닉네임이 있으면 처음 한 번 이름으로 쓴다
                    const nick = getNickname();
                    if (state && state.owner_name === '익명 농부' && nick) {
                        act('name/', { name: nick });
                    }
                });

                tickTimer = setInterval(tick, TICK_MS);
                syncTimer = setInterval(() => {
                    if (tab === 'field') pull();
                }, RESYNC_MS);
            },
            destroy() {
                dead = true;
                clearInterval(tickTimer);
                clearInterval(syncTimer);
                if (el) el.removeEventListener('click', onClick);
            },
        };
    },
};
