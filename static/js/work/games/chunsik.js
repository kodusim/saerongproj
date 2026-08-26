/* 자네 이름은 이쟈부터 춘식이여! — 『농촌 맥시멈 청년』 원작 기반 선택형 스토리.

   매 장면마다 선택지가 있고, 정해진 한 갈래만 다음 장면으로 이어진다.
   나머지는 전부 그 자리에서 게임 오버 — 왜 잘못됐는지 설명을 붙여서 보여준다.
   엔딩은 단 하나의 루트에만 있다. */

const STORY = {
    start: {
        title: '부름',
        text: `화제의 작품 『농촌 맥시멈 청년』 원작 기반 게임 —
            『자네 이름은 이쟈부터 춘식이여!』<br><br>
            이마, 등, 목도 모자라 팔뚝까지 땀이 흘러내리는 여름날. 태풍이 오기 전에
            콩 지지대를 다 세워야 하는 정 씨. 얼마 남지 않은 일을 마저 끝내는데,
            귓대기를 울려대는 매미소리를 뚫고 누군가 부른다.<br><br>
            &ldquo;어이, 정 씨! 쉬면서 해.&rdquo;<br>
            영석 삼촌이 그늘막에 서서 손짓하고 있다.`,
        choices: [
            { label: '삼촌, 무슨 일이래요? (말을 건다)', next: 'magazine' },
            {
                label: '못 들은 척, 지지대만 마저 세운다 (무시한다)',
                gameover: `정 씨는 결국 지지대를 다 세웠지만, 서운해진 삼촌은 그 뒤로
                    마을 소식을 하나도 알려주지 않았다.<br><br>
                    잡지도, 게임도, 이야기도 여기서 끝.
                    <span class="gm-vn-why">무시는 관계를 무너뜨린다.</span>`,
            },
            {
                label: '일단 다가가서 삼촌을 팬다 (일단 때리고 본다)',
                gameover: `영문도 모른 채 두들겨 맞은 영석 삼촌은 그 길로 파출소로
                    향했다.<br><br>
                    정 씨는 콩밭 대신 유치장 벤치에 눕게 되었다.
                    <span class="gm-vn-why">대화가 필요할 땐 주먹보다 입이 먼저다.</span>`,
            },
        ],
    },

    magazine: {
        title: '잡지',
        text: `삼촌이 손에 든 잡지를 툭툭 치며 말했다.<br><br>
            &ldquo;그, 저, 너 저번께 잡지 모델인지 뭐시기, 한다 했던 거. 인쇄 됐다고
            회관으로 몇 부 왔다대.&rdquo;<br><br>
            표지를 넘겨보니 땀에 젖은 러닝셔츠 차림의 정 씨가 대문짝만하게 실려 있다.
            삼촌이 씩 웃으며 한 가지를 더 얹는다.<br><br>
            &ldquo;회관에도 몇 부 돌리고, 옆 마을 이장한테도 자랑 좀 해야겄다. 사진
            잘 나왔다고 소문나면 다음엔 표지 모델도 시켜준다드라. 좀 도와줄랑가?&rdquo;`,
        choices: [
            { label: '부끄럽지만 일단 거들어본다', next: 'storm_prep' },
            {
                label: '창피해서 잡지를 뺏어 도망친다',
                gameover: `정 씨는 잡지를 통째로 들고 논두렁을 따라 전력 질주했다.
                    하지만 회관엔 이미 300부가 더 있었다.<br><br>
                    마을 어귀부터 정미소까지, 정 씨의 러닝셔츠 사진이 도배됐다.
                    <span class="gm-vn-why">도망친다고 없던 일이 되지는 않는다.</span>`,
            },
            {
                label: '잡지를 그 자리에서 찢어버린다',
                gameover: `삼촌이 애써 인쇄해온 잡지를 찢은 죄로, 정 씨는 그날부로
                    마을 회관 출입 금지 명단에 올랐다.<br><br>
                    콩도 못 팔고, 옆 마을 이장 볼 낯도 없어졌다.
                    <span class="gm-vn-why">홧김에 저지른 일은 꼭 돌아온다.</span>`,
            },
        ],
    },

    storm_prep: {
        title: '태풍 전야',
        text: `해가 뉘엿뉘엿 넘어가고 하늘 한쪽이 시커멓게 몰려온다. 태풍이 예보보다
            빠르다. 지지대는 절반쯤 세웠는데, 남은 시간은 이삼십 분 남짓.<br><br>
            삼촌이 트럭에서 각목 한 무더기를 내려주며 묻는다.<br><br>
            &ldquo;춘식아, 이거 마저 세우고 갈랑가, 아니면 밤새 버틸 만큼만 대충
            묶고 얼른 대피할랑가?&rdquo;`,
        choices: [
            { label: '남은 지지대를 끝까지, 야무지게 세운다', next: 'night_watch' },
            {
                label: '대충 몇 개만 묶고 서둘러 몸을 피한다',
                gameover: `대충 묶은 지지대는 태풍의 첫 돌풍에 우수수 쓰러졌다.
                    다음날 콩밭은 흔적도 없이 눕고 말았다.<br><br>
                    마을 사람들은 그 뒤로 정 씨를 &lsquo;대충 춘식이&rsquo;라 불렀다.
                    <span class="gm-vn-why">서두르다 놓친 마무리는 꼭 표가 난다.</span>`,
            },
            {
                label: '이 정도면 됐다며 그냥 집으로 간다',
                gameover: `정 씨는 절반만 세운 지지대를 남긴 채 집으로 향했다.
                    태풍은 기다려주지 않았다.
                    <span class="gm-vn-why">반쯤 한 일은 안 한 것과 같다.</span>`,
            },
        ],
    },

    night_watch: {
        title: '밤',
        text: `지지대를 다 세우고 나니 빗방울이 굵어지기 시작했다. 밤새 바람 소리가
            지붕을 흔든다. 라디오에서 정전 대비 방송이 흘러나오고, 창밖 콩밭 쪽에서
            뭔가 펄럭이는 소리가 들린다.<br><br>
            잠이 오지 않는 정 씨. 이대로 잘지, 나가서 한 번 더 살펴볼지 고민된다.`,
        choices: [
            {
                label: '우비를 걸치고 나가 비닐하우스 문단속을 한 번 더 확인한다',
                next: 'morning_check',
            },
            {
                label: '무섭지만 그냥 이불을 뒤집어쓰고 잔다',
                gameover: `펄럭이던 소리는 열려 있던 비닐하우스 문이었다. 바람이
                    들이쳐 하우스가 통째로 뒤집혔다.<br><br>
                    아침에 정 씨가 본 건 밭이 아니라 비닐 뭉치였다.
                    <span class="gm-vn-why">불안한 소리는 이유가 있어서 난다.</span>`,
            },
        ],
    },

    morning_check: {
        title: '아침',
        text: `밤새 씨름한 끝에 하우스 문을 단단히 걸어 잠그고 겨우 눈을 붙였다.
            아침, 태풍이 지나가고 해가 다시 쨍하다. 마당엔 나뭇가지와 흙탕물이
            어지럽고, 저 멀리 콩밭이 보인다.<br><br>
            가장 먼저 뭘 확인해야 할까.`,
        choices: [
            { label: '세워둔 지지대와 콩부터 살핀다', next: 'village_thanks' },
            {
                label: '잡지와 사진부터 젖지 않았는지 챙긴다',
                gameover: `정 씨가 잡지 상자를 끌어안고 감격하는 사이, 물꼬가 터진
                    콩밭은 흙탕물에 잠겨버렸다. 삼촌이 뒤늦게 뛰어왔지만 이미 늦었다.
                    <span class="gm-vn-why">순서를 잘못 정하면 지킬 수 있던 것도
                    잃는다.</span>`,
            },
        ],
    },

    village_thanks: {
        title: '수확',
        text: `다행이다. 어젯밤 야무지게 세운 지지대 덕에 콩들은 대부분 꼿꼿이
            버텨냈다. 옆집 밭은 절반이 쓰러졌는데, 정 씨네 밭만 멀쩡하다는 소문이
            순식간에 퍼졌다.<br><br>
            영석 삼촌이 흙탕물을 첨벙거리며 뛰어와 정 씨의 등을 두드린다.<br><br>
            &ldquo;역시 춘식이여! 이 정도면 게임 엔딩도 하나로 딱 정해지겄다!&rdquo;`,
        choices: [
            { label: '겸연쩍게 웃으며 다시 일하러 간다', next: 'ending' },
            {
                label: '잡지 표지처럼 포즈를 잡아본다',
                gameover: `미끄덩! 진흙탕에 넘어진 정 씨의 모습이 그대로 다음 호
                    표지에 실렸다. 태풍도 이겨낸 청년이 진흙에는 못 이겼다.
                    <span class="gm-vn-why">승리에 취해 방심하면 꼭 사달이 난다.</span>`,
            },
        ],
    },

    ending: {
        title: '엔딩',
        ending: true,
        text: `『자네 이름은 이쟈부터 춘식이여!』 — TRUE ENDING<br><br>
            콩밭을 지켜낸 정 씨는 그날부로 마을에서 정식으로 &lsquo;춘식이&rsquo;가
            되었다. 삼촌은 그 잡지를 옆 마을 이장한테까지 들고 가 자랑했고, 표지엔
            두고두고 회자될 별명 하나가 남았다 — &lsquo;태풍보다 억센 청년&rsquo;.
            <br><br>
            매미 소리, 땀에 젖은 러닝셔츠, 그리고 태풍보다 억센 뚝심 — 이것이 이
            여름을 버텨낸 청년의 이야기다.<br><br>
            수고했다, 춘식아.
            <br><br>
            <span style="opacity:.6;font-size:11px">
                화제의 작품 『농촌 맥시멈 청년』 원작 기반
            </span>`,
    },
};

export default {
    id: 'chunsik',
    name: '자네 이름은 이쟈부터 춘식이여!',
    icon: '🌾',
    desc: '『농촌 맥시멈 청년』 원작 기반 · 선택형 스토리',

    create(ctx) {
        let el = null;
        let node = null;
        let score = 0;
        let done = false;

        function render() {
            if (!el || done) return;
            el.innerHTML = `
                <div class="gm-vn">
                    <div class="gm-vn-text">${node.text}</div>
                    <div class="gm-vn-choices">
                        ${node.choices.map((c, i) => `
                            <button class="gm-vn-choice" type="button" data-i="${i}">
                                <span class="gm-vn-num">${i + 1}</span>
                                <span class="gm-vn-label">${c.label}</span>
                            </button>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        function goto(id) {
            node = STORY[id];
            ctx.setInfo(node.title ? `<b>${node.title}</b>` : '');
            if (node.ending) {
                score += 200;
                done = true;
                ctx.setScore(score);
                ctx.end(score, node.text);
                return;
            }
            ctx.setScore(score);
            render();
        }

        function choose(i) {
            if (done || !node || !node.choices) return;
            const c = node.choices[i];
            if (!c) return;
            if (c.next) {
                score += 100;
                goto(c.next);
            } else if (c.gameover) {
                done = true;
                ctx.end(score, c.gameover);
            }
        }

        function onClick(e) {
            const btn = e.target.closest('.gm-vn-choice');
            if (btn) choose(Number(btn.dataset.i));
        }

        function onKey(e) {
            const i = Number(e.key) - 1;
            if (Number.isInteger(i) && i >= 0) {
                e.preventDefault();
                choose(i);
            }
        }

        return {
            mount(stage) {
                el = stage;
                el.addEventListener('click', onClick);
                document.addEventListener('keydown', onKey);
                ctx.setScore(0);
                goto('start');
            },
            destroy() {
                done = true;
                document.removeEventListener('keydown', onKey);
                if (el) el.removeEventListener('click', onClick);
            },
        };
    },
};
