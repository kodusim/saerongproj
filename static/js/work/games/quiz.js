/* 누나의 과외수업 — 식을 보고 답이 있는 자리(좌/중/우)를 고른다.

   원작처럼 제한시간이 짧고, 연속으로 맞히면 콤보가 붙는다.
   키보드 ← ↓ → 와 1 2 3 도 받는다. */

const LIVES = 3;
const BASE_MS = 4200;
const MIN_MS = 1500;

function randInt(a, b) {
    return a + Math.floor(Math.random() * (b - a + 1));
}

/** 단계가 오를수록 수가 커지고 곱셈이 섞인다. */
function makeQuestion(level) {
    const hard = level > 6;
    const ops = hard ? ['+', '-', '×'] : ['+', '-'];
    const op = ops[randInt(0, ops.length - 1)];
    const span = Math.min(9 + level * 3, 60);

    let a;
    let b;
    let answer;
    if (op === '×') {
        a = randInt(2, 9);
        b = randInt(2, 9);
        answer = a * b;
    } else if (op === '+') {
        a = randInt(1, span);
        b = randInt(1, span);
        answer = a + b;
    } else {
        a = randInt(1, span);
        b = randInt(1, a);          // 음수가 안 나오게
        answer = a - b;
    }

    // 오답 두 개 — 정답에 가깝게 만들어야 헷갈린다
    const wrongs = new Set();
    while (wrongs.size < 2) {
        const delta = randInt(1, Math.max(2, Math.round(Math.abs(answer) * 0.2) + 3));
        const cand = answer + (Math.random() < 0.5 ? -delta : delta);
        if (cand !== answer && cand >= 0) wrongs.add(cand);
    }

    const choices = [answer, ...wrongs];
    for (let i = choices.length - 1; i > 0; i -= 1) {
        const j = randInt(0, i);
        [choices[i], choices[j]] = [choices[j], choices[i]];
    }

    return { text: `${a} ${op} ${b}`, answer, choices, at: choices.indexOf(answer) };
}

export default {
    id: 'quiz',
    name: '누나의 과외수업',
    icon: '📐',
    desc: '답이 있는 자리를 빠르게',

    create(ctx) {
        let el = null;
        let raf = null;
        let q = null;
        let startedAt = 0;
        let limit = BASE_MS;
        let level = 1;
        let lives = LIVES;
        let combo = 0;
        let score = 0;
        let solved = 0;
        let locked = false;
        let done = false;

        const POS = ['좌', '중', '우'];

        function paint() {
            el.innerHTML = `
                <div class="gm-quiz">
                    <div class="gm-quiz-timer"><div class="gm-quiz-bar" id="gm-qbar"></div></div>
                    <div class="gm-quiz-q">${q.text} = <span class="gm-quiz-blank">?</span></div>
                    <div class="gm-quiz-choices">
                        ${q.choices.map((c, i) => `
                            <button class="gm-quiz-c" type="button" data-i="${i}">
                                <span class="gm-quiz-pos">${POS[i]}</span>
                                <span class="gm-quiz-val">${c}</span>
                            </button>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        function info() {
            ctx.setInfo(
                `${level}단계 · 목숨 <b>${'♥'.repeat(lives)}${'♡'.repeat(LIVES - lives)}</b>`
                + ` · 콤보 <b>${combo}</b> · 맞힘 <b>${solved}</b>`
            );
        }

        function nextQuestion() {
            q = makeQuestion(level);
            limit = Math.max(MIN_MS, BASE_MS - level * 180);
            startedAt = Date.now();
            locked = false;
            paint();
            info();
        }

        function loop() {
            if (done) return;
            const left = limit - (Date.now() - startedAt);
            const bar = document.getElementById('gm-qbar');
            if (bar) {
                const pct = Math.max(0, (left / limit) * 100);
                bar.style.width = `${pct}%`;
                bar.classList.toggle('warn', pct < 30);
            }
            if (left <= 0 && !locked) answer(-1);
            raf = requestAnimationFrame(loop);
        }

        function answer(i) {
            if (locked || done) return;
            locked = true;

            const correct = i === q.at;
            const btns = el.querySelectorAll('.gm-quiz-c');
            if (btns[q.at]) btns[q.at].classList.add('right');
            if (i >= 0 && !correct && btns[i]) btns[i].classList.add('wrong');

            if (correct) {
                combo += 1;
                solved += 1;
                const speed = Math.max(0, 1 - (Date.now() - startedAt) / limit);
                score += Math.round(50 + level * 10 + combo * 5 + speed * 50);
                ctx.setScore(score);
                if (solved % 3 === 0) level += 1;
            } else {
                combo = 0;
                lives -= 1;
            }
            info();

            setTimeout(() => {
                if (done) return;
                if (lives <= 0) {
                    done = true;
                    cancelAnimationFrame(raf);
                    ctx.end(score, `${solved}문제 정답 · ${level}단계까지`);
                    return;
                }
                nextQuestion();
            }, correct ? 260 : 700);
        }

        function onClick(e) {
            const btn = e.target.closest('.gm-quiz-c');
            if (btn) answer(Number(btn.dataset.i));
        }

        function onKey(e) {
            const map = {
                ArrowLeft: 0, ArrowDown: 1, ArrowRight: 2, 1: 0, 2: 1, 3: 2,
            };
            const i = map[e.key];
            if (i === undefined) return;
            e.preventDefault();
            answer(i);
        }

        return {
            mount(stage) {
                el = stage;
                el.addEventListener('click', onClick);
                document.addEventListener('keydown', onKey);
                ctx.setScore(0);
                nextQuestion();
                loop();
            },
            destroy() {
                done = true;
                cancelAnimationFrame(raf);
                document.removeEventListener('keydown', onKey);
                if (el) el.removeEventListener('click', onClick);
            },
        };
    },
};
