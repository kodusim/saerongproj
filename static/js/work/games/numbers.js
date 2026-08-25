/* 막내의 하나둘셋 — 12칸에 흩어진 번호를 1부터 순서대로 누른다.

   원작은 판을 지울 때마다 다음 판이 나오는 방식. 여기서는 60초 타임어택으로,
   판을 하나 지울 때마다 칸이 늘어나 점점 어려워진다. */

const TOTAL_SEC = 60;
const START_CELLS = 12;
const MAX_CELLS = 25;
const CLEAR_SCORE = 100;
const MISS_PENALTY = 20;

function shuffled(n) {
    const a = Array.from({ length: n }, (_, i) => i + 1);
    for (let i = a.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}

export default {
    id: 'numbers',
    name: '막내의 하나둘셋',
    icon: '🔢',
    desc: '흩어진 번호를 1부터 순서대로',

    create(ctx) {
        let el = null;
        let timer = null;
        let endsAt = 0;
        let score = 0;
        let next = 1;
        let cells = START_CELLS;
        let board = [];
        let cleared = 0;
        let misses = 0;
        let done = false;

        function paint() {
            el.innerHTML = `
                <div class="gm-num-grid" style="--cols:${Math.ceil(Math.sqrt(cells))}">
                    ${board.map((n) => `
                        <button class="gm-num${n < next ? ' done' : ''}" type="button"
                                data-n="${n}" ${n < next ? 'disabled' : ''}>${n}</button>
                    `).join('')}
                </div>
            `;
        }

        function newBoard() {
            board = shuffled(cells);
            next = 1;
            paint();
        }

        function tick() {
            const left = Math.max(0, endsAt - Date.now());
            ctx.setInfo(
                `남은 시간 <b>${(left / 1000).toFixed(1)}초</b>`
                + ` · 지운 판 <b>${cleared}</b> · 실수 <b>${misses}</b>`
                + ` · 다음 <b>${next}</b>`
            );
            if (left <= 0) finish();
        }

        function finish() {
            if (done) return;
            done = true;
            clearInterval(timer);
            ctx.end(score, `${cleared}판 클리어 · 실수 ${misses}회`);
        }

        function onClick(e) {
            const btn = e.target.closest('.gm-num');
            if (!btn || done) return;
            const n = Number(btn.dataset.n);

            if (n !== next) {
                misses += 1;
                score = Math.max(0, score - MISS_PENALTY);
                ctx.setScore(score);
                btn.classList.add('wrong');
                setTimeout(() => btn.classList.remove('wrong'), 200);
                return;
            }

            btn.classList.add('done');
            btn.disabled = true;
            next += 1;

            if (next > cells) {
                cleared += 1;
                score += CLEAR_SCORE + cells;
                ctx.setScore(score);
                cells = Math.min(MAX_CELLS, cells + 1);
                newBoard();
            }
        }

        return {
            mount(stage) {
                el = stage;
                el.addEventListener('click', onClick);
                ctx.setScore(0);
                endsAt = Date.now() + TOTAL_SEC * 1000;
                newBoard();
                tick();
                timer = setInterval(tick, 100);
            },
            destroy() {
                done = true;
                clearInterval(timer);
                if (el) el.removeEventListener('click', onClick);
            },
        };
    },
};
