/* 미니게임 모음 — 그룹웨어 '주소록' 탭 / VS Code 'games.md'.

   컴투스 '액션 퍼즐 패밀리'(2004~) 에 있던 게임들을 규칙만 참고해 새로 만든 것이다.
   원본 리소스는 쓰지 않았다.

   테마별로 DOM 을 두 벌 만들지 않는다. 게임은 상태를 들고 도는 데다 타이머까지
   있어서 두 벌에 동시에 그리면 낭비가 크다. 대신 **지금 보이는 테마의 root 에만**
   그리고, 테마가 바뀌면 그쪽 root 로 다시 붙인다(remount). */
import { $ } from '../../lib/dom.js';
import { isVscode, onThemeChange } from '../state.js';

import numbers from './numbers.js';
import memory from './memory.js';
import quiz from './quiz.js';
import pop from './pop.js';

const GAMES = [numbers, memory, quiz, pop];
const BEST_KEY = 'work_game_best';

let current = null;      // { def, instance }
let root = null;

/* ---------------- 최고 점수 (브라우저에만 저장) ---------------- */

function allBest() {
    try {
        return JSON.parse(localStorage.getItem(BEST_KEY) || '{}');
    } catch {
        return {};
    }
}

function bestOf(id) {
    const v = allBest()[id];
    return typeof v === 'number' ? v : 0;
}

function saveBest(id, score) {
    if (score <= bestOf(id)) return false;
    const all = allBest();
    all[id] = score;
    try {
        localStorage.setItem(BEST_KEY, JSON.stringify(all));
    } catch { /* 저장 실패는 무시 */ }
    return true;
}

/* ---------------- 화면 ---------------- */

function activeRoot() {
    return $(isVscode() ? 'vc-gm-root' : 'gm-root');
}

function renderList() {
    if (!root) return;
    root.innerHTML = `
        <div class="gm-intro">
            옛날 <b>액션 퍼즐 패밀리</b> 에 있던 게임들을 규칙만 참고해 다시 만들었습니다.
            점수는 이 브라우저에만 저장됩니다.
        </div>
        <div class="gm-cards">
            ${GAMES.map((g) => `
                <button class="gm-card" type="button" data-id="${g.id}">
                    <span class="gm-card-ic">${g.icon}</span>
                    <span class="gm-card-name">${g.name}</span>
                    <span class="gm-card-desc">${g.desc}</span>
                    <span class="gm-card-best">최고 ${bestOf(g.id).toLocaleString()}점</span>
                </button>
            `).join('')}
        </div>
    `;
}

function renderFrame(def) {
    root.innerHTML = `
        <div class="gm-bar">
            <button class="gm-btn" type="button" data-act="back">← 목록</button>
            <span class="gm-bar-name">${def.name}</span>
            <span class="gm-spacer"></span>
            <span class="gm-stat">점수 <b id="gm-score">0</b></span>
            <span class="gm-stat">최고 <b id="gm-best">${bestOf(def.id).toLocaleString()}</b></span>
            <button class="gm-btn" type="button" data-act="restart">다시</button>
        </div>
        <div class="gm-info" id="gm-info"></div>
        <div class="gm-stage" id="gm-stage"></div>
    `;
}

/** 게임이 쓰는 도구 모음 */
function makeCtx(def) {
    return {
        setScore(n) {
            const el = $('gm-score');
            if (el) el.textContent = Number(n).toLocaleString();
        },
        setInfo(html) {
            const el = $('gm-info');
            if (el) el.innerHTML = html;
        },
        /** 게임이 끝났을 때 — 결과와 다시하기 버튼을 띄운다 */
        end(score, message) {
            const isNew = saveBest(def.id, score);
            const bestEl = $('gm-best');
            if (bestEl) bestEl.textContent = bestOf(def.id).toLocaleString();

            const stage = $('gm-stage');
            if (!stage) return;
            stage.innerHTML = `
                <div class="gm-over">
                    <div class="gm-over-title">${isNew ? '🎉 최고 기록!' : '게임 종료'}</div>
                    <div class="gm-over-score">${Number(score).toLocaleString()}점</div>
                    ${message ? `<div class="gm-over-msg">${message}</div>` : ''}
                    <button class="gm-btn primary" type="button" data-act="restart">다시 하기</button>
                    <button class="gm-btn" type="button" data-act="back">목록으로</button>
                </div>
            `;
        },
    };
}

function stopCurrent() {
    if (current && current.instance && current.instance.destroy) {
        current.instance.destroy();
    }
    current = null;
}

function startGame(def) {
    stopCurrent();
    renderFrame(def);
    const ctx = makeCtx(def);
    const instance = def.create(ctx);
    current = { def, instance };
    instance.mount($('gm-stage'));
}

function backToList() {
    stopCurrent();
    renderList();
}

/* ---------------- 초기화 ---------------- */

/** 테마가 바뀌면 그쪽 root 로 다시 붙인다. 진행 중이던 게임은 처음부터. */
function remount() {
    root = activeRoot();
    if (!root) return;
    if (current) startGame(current.def);
    else renderList();
}

export function initGames() {
    // 두 테마의 root 모두에 위임 클릭을 걸어둔다 (어느 쪽이 보이든 동작하도록)
    ['gm-root', 'vc-gm-root'].forEach((id) => {
        const el = $(id);
        if (!el) return;
        el.addEventListener('click', (e) => {
            const card = e.target.closest('.gm-card');
            if (card) {
                const def = GAMES.find((g) => g.id === card.dataset.id);
                if (def) startGame(def);
                return;
            }
            const btn = e.target.closest('[data-act]');
            if (!btn) return;
            if (btn.dataset.act === 'back') backToList();
            if (btn.dataset.act === 'restart' && current) startGame(current.def);
        });
    });

    onThemeChange(remount);
    remount();
}

/** 다른 화면으로 넘어갈 때 타이머를 확실히 멈춘다. */
export function suspendGames() {
    stopCurrent();
    if (root) renderList();
}
