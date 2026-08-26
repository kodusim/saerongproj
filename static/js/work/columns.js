/* 표의 열 너비 수동 조절.

   너비는 표 wrap 의 CSS 변수(--w-*)로 들어간다. 헤더와 모든 행이 같은 변수를
   보므로, 행을 다시 그려도(폴링·재렌더) 조정한 너비가 그대로 남는다.
   조정값은 localStorage 에 저장해서 다음 방문에도 유지한다.

   문서함/자료실/공지사항은 서로 다른 <div class="gw-table-wrap"> 이라 CSS 변수를
   상속으로 공유하지 못한다 — 변수 이름이 같아도 값은 각자 것이다. "제목·작성자·
   날짜"처럼 여러 표에 같은 뜻으로 있는 열은 group 을 지정하면, 드래그할 때
   groupRegistry 에 등록된 다른 표의 같은 group 열에도 즉시 같은 폭을 적용하고
   SHARED_KEY 에 공용으로 저장한다 — 엑셀처럼 표 전체가 같이 움직이는 느낌. */

const MIN_PX = 28;
const MAX_PX = 900;
const SHARED_KEY = 'work_cols_shared';

/** group 이름 → 그 그룹에 속한 { wrap, varName } 목록 (모듈 전역, 페이지 생애 동안 누적). */
const groupRegistry = new Map();

function loadShared() {
    try {
        return JSON.parse(localStorage.getItem(SHARED_KEY) || '{}');
    } catch {
        return {};
    }
}

function saveSharedValue(group, px) {
    const shared = loadShared();
    shared[group] = `${px}px`;
    try {
        localStorage.setItem(SHARED_KEY, JSON.stringify(shared));
    } catch { /* 저장 실패는 무시 — 너비는 이번 세션에만 남는다 */ }
}

function applyToGroup(group, px, skipWrap) {
    (groupRegistry.get(group) || []).forEach(({ wrap, varName }) => {
        if (wrap === skipWrap) return;
        wrap.style.setProperty(varName, `${px}px`);
    });
}

/**
 * @param {object}   opts
 * @param {Element}  opts.wrap     .gw-table-wrap (CSS 변수가 붙는 곳)
 * @param {Element}  opts.head     .gw-table-head
 * @param {Array}    opts.cols     [{ cls, varName, group? }, ...] — group 이 있으면
 *                                 같은 group 을 쓰는 다른 표의 열과 폭이 동기화된다.
 * @param {string}   opts.storageKey  group 없는(표 고유) 열의 저장 키
 */
export function initColumnResize({ wrap, head, cols, storageKey }) {
    if (!wrap || !head) return;

    const defaults = {};
    cols.forEach(({ varName }) => {
        defaults[varName] = getComputedStyle(wrap).getPropertyValue(varName).trim();
    });

    function save() {
        const out = {};
        cols.forEach(({ varName, group }) => {
            if (group) return; // 공유 열은 SHARED_KEY 쪽에 저장한다
            const v = wrap.style.getPropertyValue(varName);
            if (v) out[varName] = v;
        });
        try {
            localStorage.setItem(storageKey, JSON.stringify(out));
        } catch { /* 저장 실패는 무시 — 너비는 이번 세션에만 남는다 */ }
    }

    function restore() {
        let saved;
        try {
            saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
        } catch {
            saved = {};
        }
        Object.entries(saved).forEach(([varName, value]) => {
            if (typeof value === 'string' && /^\d+(\.\d+)?px$/.test(value)) {
                wrap.style.setProperty(varName, value);
            }
        });

        const shared = loadShared();
        cols.forEach(({ varName, group }) => {
            if (!group) return;
            const value = shared[group];
            if (typeof value === 'string' && /^\d+(\.\d+)?px$/.test(value)) {
                wrap.style.setProperty(varName, value);
            }
        });
    }

    function currentPx(varName) {
        const raw = wrap.style.getPropertyValue(varName)
            || getComputedStyle(wrap).getPropertyValue(varName);
        return parseFloat(raw) || 0;
    }

    restore();

    cols.forEach(({ cls, varName, group }) => {
        const cell = head.querySelector(`.${cls}`);
        if (!cell) return;

        if (group) {
            if (!groupRegistry.has(group)) groupRegistry.set(group, []);
            groupRegistry.get(group).push({ wrap, varName });
        }

        const handle = document.createElement('span');
        handle.className = 'col-resizer';
        handle.title = '드래그해서 너비 조절 · 더블클릭하면 기본값';
        cell.appendChild(handle);

        handle.addEventListener('mousedown', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const startX = e.clientX;
            const startW = currentPx(varName);
            handle.classList.add('dragging');
            document.body.style.userSelect = 'none';
            document.body.style.cursor = 'col-resize';

            function onMove(ev) {
                const next = Math.round(Math.min(MAX_PX, Math.max(MIN_PX, startW + (ev.clientX - startX))));
                wrap.style.setProperty(varName, `${next}px`);
                if (group) applyToGroup(group, next, wrap);
            }

            function onUp() {
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
                handle.classList.remove('dragging');
                document.body.style.userSelect = '';
                document.body.style.cursor = '';
                if (group) saveSharedValue(group, currentPx(varName));
                save();
            }

            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
        });

        handle.addEventListener('dblclick', (e) => {
            e.preventDefault();
            e.stopPropagation();
            wrap.style.removeProperty(varName);
            if (defaults[varName]) wrap.style.setProperty(varName, defaults[varName]);
            if (group) {
                const px = currentPx(varName);
                applyToGroup(group, px, wrap);
                saveSharedValue(group, px);
            }
            save();
        });
    });
}
