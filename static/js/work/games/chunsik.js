/* 자네 이름은 이쟈부터 춘식이여! — 『농촌 맥시멈 청년』 원작 기반 선택형 스토리.

   매 장면마다 선택지가 있고, 정해진 한 갈래만 다음 장면으로 이어진다.
   나머지는 전부 그 자리에서 게임 오버 — 왜 잘못됐는지 설명을 붙여서 보여준다.
   엔딩은 단 하나의 루트에만 있다.

   원작의 농촌 배경 · 잡지 촬영 에피소드 · 영석 삼촌과의 관계를 살리되,
   원작에 있는 폭력적인 장면은 전부 빼고 두 사람의 잔잔한 로맨스로
   각색했다 — 스킨십은 손을 맞잡는 정도까지만. */

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
                    잡지도, 이야기도 여기서 끝.
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
            회관으로 몇 부 왔다대. 너 갖다주려고 친히 여기까지 행차하셨다 이거지.&rdquo;<br><br>
            축축한 장갑을 벗어던진 정 씨는 멋쩍게 표지를 들여다봤다. 낯선 모습의
            자신이 헐벗고 있는 게 퍽 낯간지러웠다.<br><br>
            &ldquo;서울 놈들, 그거 다 사기꾼들이에요. 사람 홀딱 벗겨놓고 꼴랑
            백이십 원 주고, 온 국민이 다 보게 만드는 게 사기지 뭐예요.&rdquo;<br>
            &ldquo;허허, 참, 저가 하겠다 해놓곤.&rdquo;<br><br>
            삼촌이 혀를 차며 트럭 기어를 넣었다. 회관 쪽으로 흙먼지를 날리며
            트럭이 달렸다.`,
        choices: [
            {
                label: '달리는 트럭에서 냅다 뛰어내리려 한다',
                gameover: `기겁한 삼촌이 정 씨를 붙잡느라 트럭이 그대로 논두렁에
                    처박혔다. 둘 다 크게 다치진 않았지만, 그날 이후로 삼촌은
                    정 씨를 조수석에 태우지 않았다.
                    <span class="gm-vn-why">화가 나도 달리는 차에서 뛰어내리면
                    안 된다.</span>`,
            },
            { label: '투덜대면서도 순순히 따라간다', next: 'teasing' },
            {
                label: '잡지를 창밖으로 던져버린다',
                gameover: `삼촌이 애써 인쇄해온 잡지가 빗길 위로 나뒹굴었다.
                    정 씨는 그날부로 &lsquo;버르장머리 없는 놈&rsquo;이라는 별명을
                    하나 더 얻었다.
                    <span class="gm-vn-why">홧김에 저지른 일은 꼭 돌아온다.</span>`,
            },
        ],
    },

    teasing: {
        title: '회관',
        text: `트럭이 회관 앞에 멈추자, 정자에 둘러앉아 있던 삼촌들이 우르르
            몰려들었다. 잡지 페이지를 이리 뒤적, 저리 뒤적이던 삼촌들은 정 씨가
            나온 페이지를 펴 보이며 낄낄댔다.<br><br>
            &ldquo;주인공 왔네, 왔어!&rdquo;<br>
            두터운 손들이 정 씨의 등짝을 철썩철썩 두드렸다.<br><br>
            &ldquo;역시 젊은 놈이, 몸이 좋긴 좋다니께.&rdquo;<br>
            귀까지 벌게진 정 씨는 어디로 눈을 둬야 할지 몰랐다.`,
        choices: [
            {
                label: '정색하며 삼촌들에게 쏘아붙인다',
                gameover: `정 씨의 날 선 말에 정자엔 찬바람이 돌았다. 장난이
                    심했다 해도, 마을 어른들 앞에서 대놓고 쏘아붙인 청년의
                    태도는 두고두고 입방아에 올랐다.
                    <span class="gm-vn-why">놀림도 정도껏 받아넘겨야 뒤끝이
                    없다.</span>`,
            },
            { label: '웃어넘기고 슬쩍 자리를 피한다', next: 'storm_prep' },
            {
                label: '부끄러움에 그 자리에 얼어붙어 계속 놀림감이 된다',
                gameover: `정 씨는 얼굴이 새빨개진 채로 한참을 서 있었다.
                    그 사이 놀림은 점점 짓궂어졌고, 결국 눈물까지 찔끔 흘리며
                    도망치듯 집으로 뛰어갔다.
                    <span class="gm-vn-why">가끔은 웃어넘기는 것도 요령이다.</span>`,
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
            { label: '남은 지지대를 끝까지, 야무지게 세운다', next: 'night_together' },
        ],
    },

    night_together: {
        title: '밤',
        text: `지지대를 다 세우고 나니 빗방울이 굵어지기 시작했다. 흠뻑 젖어
            들어온 정 씨를 보고 삼촌이 서둘러 라면을 끓였다.<br><br>
            &ldquo;세 개 끓이면 양 맞겠나?&rdquo;<br>
            &ldquo;삼촌 생각하면 네 개는 끓이셔야지요.&rdquo;<br><br>
            삼촌이 실없이 웃으며 수건을 던져줬다. 젖은 머리를 닦아주겠다며
            다가온 삼촌의 손이 정 씨의 정수리를 슥슥 헝클였다. 가까워진 거리에,
            정 씨의 심장이 괜히 쿵 뛰었다.`,
        choices: [
            {
                label: '괜히 민망해서 자리를 피해 방으로 들어가 버린다',
                gameover: `정 씨는 라면 냄비를 남겨둔 채 방으로 숨어버렸다.
                    삼촌은 식어가는 라면을 혼자 앞에 두고 한참을 앉아 있었다.
                    <span class="gm-vn-why">마음이 있어도 자꾸 도망치면 다가오던
                    사람도 지친다.</span>`,
            },
            { label: '어색하게 웃으며 삼촌 옆에 바짝 붙어 앉는다', next: 'morning_thanks' },
            {
                label: '아무렇지 않은 척 화제를 딴 데로 돌린다',
                gameover: `정 씨는 애써 태풍 뉴스 얘기로 화제를 돌렸다. 삼촌도
                    눈치껏 맞춰주긴 했지만, 그날 이후로 둘 사이엔 미묘한 거리가
                    하나 더 생겼다.
                    <span class="gm-vn-why">마음을 숨기기만 하면 거리는 좁혀지지
                    않는다.</span>`,
            },
        ],
    },

    morning_thanks: {
        title: '아침',
        text: `밤새 씨름한 지지대 덕에 콩들은 대부분 꼿꼿이 버텨냈다. 옆집 밭은
            절반이 쓰러졌는데 정 씨네 밭만 멀쩡하다는 소문이 순식간에 퍼졌다.<br><br>
            영석 삼촌이 흙탕물을 첨벙거리며 뛰어와 정 씨의 어깨를 꽉 붙잡았다.<br><br>
            &ldquo;역시 춘식이여! 고생했다, 진짜.&rdquo;<br><br>
            웃음 짓던 삼촌의 눈빛이 문득 진지해지더니, 어깨를 잡은 손에 힘이
            살짝 들어갔다. 평소와는 조금 다른, 낯선 온도였다.`,
        choices: [
            {
                label: '괜히 어색해서 손을 뿌리치고 딴청을 피운다',
                gameover: `정 씨는 손을 슥 빼며 애먼 콩밭만 쳐다봤다. 삼촌은
                    멋쩍게 웃으며 손을 거뒀고, 그 뒤로 두 사람은 그날의 일을
                    다시 꺼내지 않았다.
                    <span class="gm-vn-why">놓친 손은 좀처럼 다시 잡기 어렵다.</span>`,
            },
            {
                label: '잡지 표지처럼 포즈를 잡아본다',
                gameover: `미끄덩! 진흙탕에 넘어진 정 씨의 모습이 그대로 다음 호
                    표지에 실렸다. 태풍도 이겨낸 청년이 진흙에는 못 이겼다.
                    <span class="gm-vn-why">분위기 파악 못 하면 꼭 사달이 난다.</span>`,
            },
            { label: '그 손을 가만히 마주 잡는다', next: 'ending' },
        ],
    },

    ending: {
        title: '엔딩',
        ending: true,
        text: `『자네 이름은 이쟈부터 춘식이여!』 — TRUE ENDING<br><br>
            콩밭을 지켜낸 정 씨는 그날부로 마을에서 정식으로 &lsquo;춘식이&rsquo;가
            되었다. 삼촌은 그 잡지를 옆 마을 이장한테까지 들고 가 자랑했고,
            표지엔 두고두고 회자될 별명 하나가 남았다 — &lsquo;태풍보다 억센
            청년&rsquo;.<br><br>
            그날 밤, 마당에 나란히 걸터앉은 두 사람 사이로 어색한 침묵이 흘렀다.
            먼저 손을 뻗은 건 삼촌이었다. 맞잡은 손 위로, 정 씨는 그동안 애써
            모른 척해온 마음을 가만히 내려놓았다.<br><br>
            &ldquo;삼촌, 저기…&rdquo;<br>
            &ldquo;알아, 나도.&rdquo;<br><br>
            매미 소리도 잦아든 여름밤, 두 사람의 어깨가 조용히 맞닿았다.<br><br>
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
    desc: '『농촌 맥시멈 청년』 원작 기반 · 선택형 스토리 로맨스',

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
