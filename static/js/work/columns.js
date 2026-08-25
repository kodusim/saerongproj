/* 표의 열 너비 수동 조절.

   너비는 표 wrap 의 CSS 변수(--w-*)로 들어간다. 헤더와 모든 행이 같은 변수를
   보므로, 행을 다시 그려도(폴링·재렌더) 조정한 너비가 그대로 남는다.
   조정값은 localStorage 에 저장해서 다음 방문에도 유지한다. */

const MIN_PX = 28;
const MAX_PX = 900;

/**
 * @param {object}   opts
 * @param {Element}  opts.wrap     .gw-table-wrap (CSS 변수가 붙는 곳)
 * @param {Element}  opts.head     .gw-table-head
 * @param {Array}    opts.cols     [{ cls: 'col-title', varName: '--w-title' }, ...]
 * @param {string}   opts.storageKey
 */
export function initColumnResize({ wrap, head, cols, storageKey }) {
    if (!wrap || !head) return;

    const defaults = {};
    cols.forEach(({ varName }) => {
        defaults[varName] = getComputedStyle(wrap).getPropertyValue(varName).trim();
    });

    function save() {
        const out = {};
        cols.forEach(({ varName }) => {
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
            return;
        }
        Object.entries(saved).forEach(([varName, value]) => {
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

    cols.forEach(({ cls, varName }) => {
        const cell = head.querySelector(`.${cls}`);
        if (!cell) return;

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
                const next = Math.min(MAX_PX, Math.max(MIN_PX, startW + (ev.clientX - startX)));
                wrap.style.setProperty(varName, `${Math.round(next)}px`);
            }

            function onUp() {
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
                handle.classList.remove('dragging');
                document.body.style.userSelect = '';
                document.body.style.cursor = '';
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
            save();
        });
    });
}
