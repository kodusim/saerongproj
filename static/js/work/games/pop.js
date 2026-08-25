/* 할매의 뽁뽁뽁뽁 — 3개 이상 이어진 블록을 눌러 터뜨린다.

   아래에서 한 줄씩 계속 밀려 올라오고, 맨 윗줄까지 차면 끝.
   한 번에 많이 터뜨릴수록 점수가 가파르게 오른다 (개수의 제곱). */

const COLS = 8;
const ROWS = 11;
const COLORS = ['r', 'y', 'g', 'b', 'p'];
const MIN_POP = 3;
const RISE_START_MS = 7000;
const RISE_MIN_MS = 2600;

const rnd = (n) => Math.floor(Math.random() * n);

export default {
    id: 'pop',
    name: '할매의 뽁뽁뽁뽁',
    icon: '🫧',
    desc: '3개 이상 이어진 걸 터뜨리기',

    create(ctx) {
        let el = null;
        let riseTimer = null;
        let grid = [];          // grid[r][c] = 색 or null,  r=0 이 맨 위
        let score = 0;
        let popped = 0;
        let rises = 0;
        let riseMs = RISE_START_MS;
        let done = false;

        const idx = (r, c) => r * COLS + c;

        function newRow() {
            return Array.from({ length: COLS }, () => COLORS[rnd(COLORS.length)]);
        }

        function paint() {
            el.innerHTML = `
                <div class="gm-pop-grid" style="--cols:${COLS}">
                    ${grid.flatMap((row, r) => row.map((c, col) => `
                        <div class="gm-pop-cell${c ? ` c-${c}` : ' empty'}"
                             data-r="${r}" data-c="${col}"></div>
                    `)).join('')}
                </div>
            `;
        }

        function info() {
            ctx.setInfo(
                `터뜨린 블록 <b>${popped}</b> · 올라온 줄 <b>${rises}</b>`
                + ` · 다음 줄까지 <b>${(riseMs / 1000).toFixed(1)}초</b>`
            );
        }

        /** 같은 색으로 이어진 덩어리 (상하좌우) */
        function group(r0, c0) {
            const color = grid[r0][c0];
            if (!color) return [];
            const seen = new Set([idx(r0, c0)]);
            const stack = [[r0, c0]];
            const out = [];
            while (stack.length) {
                const [r, c] = stack.pop();
                out.push([r, c]);
                [[r - 1, c], [r + 1, c], [r, c - 1], [r, c + 1]].forEach(([nr, nc]) => {
                    if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) return;
                    if (seen.has(idx(nr, nc))) return;
                    if (grid[nr][nc] !== color) return;
                    seen.add(idx(nr, nc));
                    stack.push([nr, nc]);
                });
            }
            return out;
        }

        /** 빈칸 위의 블록을 아래로 떨어뜨린다 */
        function settle() {
            for (let c = 0; c < COLS; c += 1) {
                const stack = [];
                for (let r = ROWS - 1; r >= 0; r -= 1) {
                    if (grid[r][c]) stack.push(grid[r][c]);
                }
                for (let r = ROWS - 1, i = 0; r >= 0; r -= 1, i += 1) {
                    grid[r][c] = i < stack.length ? stack[i] : null;
                }
            }
        }

        function finish(msg) {
            if (done) return;
            done = true;
            clearInterval(riseTimer);
            ctx.end(score, msg);
        }

        function rise() {
            if (done) return;
            // 맨 윗줄에 블록이 있으면 더 밀 수 없다
            if (grid[0].some(Boolean)) {
                finish(`${rises}줄까지 버팀 · ${popped}개 제거`);
                return;
            }
            grid.shift();
            grid.push(newRow());
            rises += 1;

            // 점점 빨라진다
            riseMs = Math.max(RISE_MIN_MS, RISE_START_MS - rises * 250);
            clearInterval(riseTimer);
            riseTimer = setInterval(rise, riseMs);

            paint();
            info();
        }

        function onClick(e) {
            if (done) return;
            const cell = e.target.closest('.gm-pop-cell');
            if (!cell) return;
            const r = Number(cell.dataset.r);
            const c = Number(cell.dataset.c);
            if (!grid[r][c]) return;

            const g = group(r, c);
            if (g.length < MIN_POP) {
                cell.classList.add('nope');
                setTimeout(() => cell.classList.remove('nope'), 180);
                return;
            }

            g.forEach(([gr, gc]) => { grid[gr][gc] = null; });
            settle();

            popped += g.length;
            score += g.length * g.length * 10;
            ctx.setScore(score);
            paint();
            info();
        }

        return {
            mount(stage) {
                el = stage;
                el.addEventListener('click', onClick);
                ctx.setScore(0);

                // 아래 5줄로 시작
                grid = Array.from({ length: ROWS }, (_, r) =>
                    (r >= ROWS - 5 ? newRow() : Array(COLS).fill(null)));

                paint();
                info();
                riseTimer = setInterval(rise, riseMs);
            },
            destroy() {
                done = true;
                clearInterval(riseTimer);
                if (el) el.removeEventListener('click', onClick);
            },
        };
    },
};
