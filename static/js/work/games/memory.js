/* 할배의 기억강화 — 12칸 패턴을 기억했다가 그대로 만든다.

   원작 규칙 그대로: 누르는 **순서는 상관없고**, 칸을 누를 때마다 색이 돌아간다.
   빈칸 → 노랑(1번) → 빨강(2번) → 파랑(3번) → 다시 빈칸.
   즉 노랑은 1번, 빨강은 2번, 파랑은 3번 눌러야 그 색이 된다. */

const CELLS = 12;
const COLORS = ['', 'y', 'r', 'b'];       // '' = 빈칸
const LABEL = { '': '', y: '🐤', r: '🐔', b: '🐦' };
const LIVES = 3;

function randomTarget(filled) {
    const idx = Array.from({ length: CELLS }, (_, i) => i);
    for (let i = idx.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [idx[i], idx[j]] = [idx[j], idx[i]];
    }
    const target = Array(CELLS).fill('');
    idx.slice(0, filled).forEach((i) => {
        target[i] = COLORS[1 + Math.floor(Math.random() * 3)];
    });
    return target;
}

export default {
    id: 'memory',
    name: '할배의 기억강화',
    icon: '🧠',
    desc: '패턴을 기억해서 그대로',

    create(ctx) {
        let el = null;
        let timer = null;
        let target = [];
        let current = [];
        let phase = 'show';      // 'show' | 'input'
        let round = 1;
        let lives = LIVES;
        let score = 0;
        let done = false;

        const filledCount = () => Math.min(CELLS, 3 + Math.floor(round / 2));
        const showMs = () => Math.max(1200, 3200 - round * 150);

        function paint() {
            const shown = phase === 'show' ? target : current;
            el.innerHTML = `
                <div class="gm-mem-grid">
                    ${shown.map((c, i) => `
                        <button class="gm-mem${c ? ` c-${c}` : ''}" type="button"
                                data-i="${i}" ${phase === 'show' ? 'disabled' : ''}>${LABEL[c]}</button>
                    `).join('')}
                </div>
                ${phase === 'input' ? `
                    <div class="gm-mem-actions">
                        <span class="gm-hint">🐤 1번 · 🐔 2번 · 🐦 3번 눌러서 맞추세요</span>
                        <button class="gm-btn primary" type="button" data-check="1">확인</button>
                    </div>
                ` : ''}
            `;
        }

        function info() {
            ctx.setInfo(
                `${round}단계 · 목숨 <b>${'♥'.repeat(lives)}${'♡'.repeat(LIVES - lives)}</b>`
                + (phase === 'show' ? ' · <b>외우세요!</b>' : ' · 그대로 만들어 보세요')
            );
        }

        function startRound() {
            phase = 'show';
            target = randomTarget(filledCount());
            current = Array(CELLS).fill('');
            paint();
            info();
            timer = setTimeout(() => {
                if (done) return;
                phase = 'input';
                paint();
                info();
            }, showMs());
        }

        function check() {
            const ok = target.every((c, i) => c === current[i]);
            if (ok) {
                score += 100 + round * 20;
                ctx.setScore(score);
                round += 1;
                startRound();
                return;
            }

            lives -= 1;
            if (lives <= 0) {
                done = true;
                ctx.end(score, `${round}단계에서 종료`);
                return;
            }
            // 틀리면 정답을 잠깐 보여주고 같은 단계를 다시
            phase = 'show';
            paint();
            info();
            timer = setTimeout(() => {
                if (done) return;
                startRound();
            }, 1400);
        }

        function onClick(e) {
            if (done || phase !== 'input') return;

            if (e.target.closest('[data-check]')) {
                check();
                return;
            }
            const btn = e.target.closest('.gm-mem');
            if (!btn) return;

            const i = Number(btn.dataset.i);
            const at = COLORS.indexOf(current[i]);
            current[i] = COLORS[(at + 1) % COLORS.length];

            btn.className = `gm-mem${current[i] ? ` c-${current[i]}` : ''}`;
            btn.textContent = LABEL[current[i]];
        }

        return {
            mount(stage) {
                el = stage;
                el.addEventListener('click', onClick);
                ctx.setScore(0);
                startRound();
            },
            destroy() {
                done = true;
                clearTimeout(timer);
                if (el) el.removeEventListener('click', onClick);
            },
        };
    },
};
