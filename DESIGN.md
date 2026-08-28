# 알카포스트 디자인 규약

**알카포스트** (BL 소설 연재 플랫폼, `/bltest/`) 전용 문서.
기획은 [LB기획.md](LB기획.md), 구현체는 `templates/bl/` · `static/css/bl.css` · `static/js/bl/`.

> **이 문서의 지위**
> 여기서 정하는 건 **구조와 규칙**이다. **값(색·폭·크기·모양)은 전부 잠정이며 언제든 바뀐다.**
> - 5장까지 = **고정.** 알카포스트에 새 화면을 붙일 땐 무조건 이 규칙을 따른다.
> - 6장 = **현재 값 스냅샷.** 참고용이지 확정이 아니다. 바뀌면 이 표만 갱신한다.
>
> 구조를 이렇게 잡는 이유: 나중에 디자인을 통째로 갈아엎어도 **`bl.css` 상단의 CSS 변수와
> 컨테이너 폭 숫자만 고치면 알카포스트 전 화면이 따라오게** 하기 위해서다.
> 구조가 흔들리면 그게 안 된다.
>
> **적용 범위는 `/bltest/` 뿐이다.** 랜딩 · `/tdmprediction/` · `/work/` 는 이 문서와 무관하다.

현재 화면: 홈(목록) · 작품 상세 · 뷰어 · 작가 서재(쓰기).

---

## 1. 페이지 골격 (고정)

새 화면은 이 뼈대에서 시작한다.

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">   <!-- 필수 -->
<title>화면명 — 알카포스트</title>
<link rel="stylesheet" href="/static/css/bl.css">
</head>
<body>
<div class="bl-wrap">              <!-- 중앙 컨테이너 : 이 안에만 콘텐츠 -->
    <div class="bl-head">
        <a class="bl-logo" href="/bltest/">          <!-- 로고 : 4-6 -->
            <picture>
                <source srcset="/static/img/logo-dark.png" media="(prefers-color-scheme: dark)">
                <img src="/static/img/logo.png" alt="ARCApost">
            </picture>
        </a>
        <span class="bl-spacer"></span>
        <!-- 우측 액션 -->
    </div>
    …
</div>
<script type="module" src="/static/js/bl/<화면>.js"></script>
</body>
</html>
```

규칙:
- `<meta name="viewport">` **누락 금지.** 이거 하나 빠지면 모바일 구도가 전부 깨진다.
- 빌드 도구 없음. **순수 ES 모듈(`type="module"`) + 순수 CSS.** 프레임워크·CDN 도입 금지.
- 스타일은 전부 `bl.css`. 템플릿에 인라인 `<style>` 금지.
  (`viewer.html` 의 `style="width:auto"` 정도의 1회성 미세조정만 예외)
- 서버가 넘겨야 하는 값은 `<body data-*>` 로 싣고 JS가 읽는다. (`viewer.html` 방식)

---

## 2. 레이아웃 규칙 (고정)

### 2-1. 중앙 고정 컨테이너 — 이게 구도의 전부

```css
* { box-sizing: border-box; margin: 0; padding: 0; }   /* 전역 리셋, 필수 */

.bl-wrap {
    max-width: 900px;        /* 상한선 — 넘으면 여기서 멈춤 */
    margin: 0 auto;          /* 남는 공간을 좌우로 균등 분배 = 중앙 정렬 */
    padding: 20px 18px 60px; /* 화면 끝에 안 붙게 하는 최소 여백 */
}
```

- `max-width` + `margin: 0 auto` — **큰 화면에선 가운데, 작은 화면에선 꽉 참.**
  데스크탑용/모바일용 레이아웃을 따로 만들지 않는다. 하나가 늘었다 줄 뿐이다.
- `box-sizing: border-box` **전역 필수.** 없으면 padding이 폭 밖으로 나가 모바일에 가로 스크롤이 생긴다.
- `width: 900px` 같은 **고정폭 금지.** 항상 `max-width`.

### 2-2. 폭 등급

용도별로 상한선을 나눈다. 숫자는 잠정이지만 **"등급을 나눈다"는 원칙은 고정**이다.

| 등급 | 클래스 | 용도 | 현재 값 |
|---|---|---|---|
| 일반 | `.bl-wrap` | 홈 목록 · 작품 상세 · 작가 서재 | `900px` |
| 읽기 | `.bl-reader` | 뷰어 — 긴 본문을 읽는 화면 | `720px` |
| 좁게 | `.bl-modal-box` | 모달 · 단일 폼 | `460px` |

뷰어를 더 좁게 잡는 건 취향이 아니라 **한 줄 글자 수를 줄여 가독성을 확보**하기 위한 것이다.
새 화면은 셋 중 하나를 고른다. 새 등급이 필요하면 이 표를 먼저 고친다.

### 2-3. 세로 1열 원칙

- 목록은 `display: grid; gap: 12px` 만. **컬럼 지정 없이 1열.** (`.bl-list`)
- 카드(`.bl-card`)는 폭 100%를 채우고 세로로 쌓인다.
- 화면이 넓다고 2~3열 그리드로 바꾸지 않는다. 폰과 PC의 **구조가 동일**해야 어긋날 여지가 없다.
- 표지 썸네일 그리드 같은 멀티컬럼이 필요해지면 이 문서를 먼저 고치고 진행한다.

---

## 3. 반응형 규칙 (고정)

**미디어쿼리로 화면별 레이아웃을 각각 만들지 않는다.** flex가 알아서 접히게 짠다.

### 3-1. 가로로 늘어놓는 건 전부 `flex-wrap: wrap`

```css
.bl-head, .bl-toolbar, .bl-card-meta, .bl-tags,
.bl-hero-meta, .bl-hero-actions, .bl-reader-bar, .bl-keybox {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;    /* 좁아지면 알아서 다음 줄로 */
}
```
브레이크포인트를 정할 필요가 없다. 요소가 안 들어가면 스스로 내려간다.

### 3-2. "늘어나되, 어느 선 아래로는 안 줄고 줄바꿈"

```css
.bl-toolbar .bl-input { flex: 1; min-width: 160px; }
```
- `flex: 1` → 넓으면 남는 공간을 먹는다
- `min-width` → 그 아래로는 안 줄고, 대신 형제 요소가 다음 줄로 내려간다

툴바·폼 요소에 이 조합을 기본으로 쓴다.
남는 공간을 밀어내 우측 정렬하는 건 `.bl-spacer { flex: 1 }` 빈 요소로 처리한다.

### 3-3. 오버플로 방어 (빠뜨리기 쉬움)

- flex 자식 중 **글자가 길어질 수 있는 것**에는 `min-width: 0` 필수.
  (flex 기본값 `min-width: auto` 때문에 긴 제목이 컨테이너를 밀어낸다)
  자를 땐 `overflow:hidden; text-overflow:ellipsis; white-space:nowrap` (`.bl-ep-title` 참고)
- 한글 본문은 `word-break: keep-all` — 어절 단위로 끊는다 (`.bl-body`)
- 작가 키·URL처럼 끊을 데 없는 문자열은 `word-break: break-all` (`.bl-keybox code`)
- 여러 줄 요약은 `-webkit-line-clamp` (`.bl-card-sum` = 2줄)
- 사용자 입력 본문·줄거리는 `white-space: pre-wrap` 으로 줄바꿈을 살린다

### 3-4. 미디어쿼리는 최후 수단

- `bl.css` 의 화면폭 미디어쿼리는 **`max-width: 480px` 하나뿐이다. 늘리지 않는다.**
- 거기서 하는 일은 **padding 축소와 큰 제목 크기 미세조정 정도**로 제한.
- 미디어쿼리 안에서 `display` / `flex-direction` 을 바꿔 레이아웃을 재배치해야 한다면,
  **설계가 틀린 것**이다. 3-1 / 3-2 로 다시 짠다.

---

## 4. 색 · 테마 규칙 (고정)

### 4-1. 색은 CSS 변수로만

컴포넌트 CSS에 **hex 하드코딩 금지.** 반드시 변수를 참조한다.

```css
:root {
    --bg          /* 페이지 배경 */
    --panel       /* 카드 · 패널 · 입력창 배경 */
    --tint        /* 살짝 눌린 표면 — 태그 · 목록 hover · 코드박스 · 안내박스 */
    --line        /* 기본 테두리 */
    --line-strong /* hover 테두리 · 강조 테두리 */
    --fg          /* 본문 글자 */
    --muted       /* 보조 글자 (메타 · 도움말 · 로고 뒷글자) */
    --accent      /* 강조 (주 버튼 · focus · 내 작품 뱃지) */
    --accent-fg   /* accent 위에 얹는 글자 */
    --danger      /* 경고 · 삭제 · 비공개 */
}
```

이 **10개 축은 고정**이다. 값은 바뀌어도 이름은 유지한다.
축을 늘려야 하면 이 문서를 먼저 고친다.

`--bg` 와 `--panel` 이 같은 값일 수 있으므로(현재 둘 다 순백) **면을 구분할 땐 `--tint` 를 쓴다.**
`--bg` 를 표면 색으로 재활용하지 않는다 — 그러면 배경색을 바꾸는 순간 태그·hover가 통째로 사라진다.

### 4-2. 모노톤 원칙

알카포스트는 **흑백**이다. `--danger` 를 뺀 모든 축은 무채색(회색 계열)만 쓴다.

- 유일한 유색은 `--danger` — **삭제 · 경고 · 비공개**에만 쓴다. 이 셋 말고는 빨강을 쓰지 않는다.
- 강조는 색이 아니라 **채움(`.bl-btn.primary`) · 테두리 굵기 · 글자 굵기**로 만든다.
- 새 상태 색(성공 초록, 정보 파랑 등)을 추가하지 않는다. 필요하면 이 절을 먼저 고친다.
- 예외는 둘뿐이다:
  1. **로고** — ARCApost 워드마크가 브랜드 레드를 갖는다 (4-6). 마침 `--danger` 와 같은 계열이라
     화면은 여전히 "검정 · 흰색 · 빨강" 세 가지로만 읽힌다.
  2. **뷰어 세피아 테마** (4-4) — 브랜드 색이 아니라 장시간 읽기용 눈 보호 옵션이라 남겼다.

### 4-3. 다크모드는 변수 재정의로만

```css
@media (prefers-color-scheme: dark) { :root { /* 같은 변수, 다른 값 */ } }
```
컴포넌트 CSS를 다크모드용으로 다시 쓰지 않는다. **변수만 갈아끼운다.**
알카포스트 기본은 **OS 설정을 따라간다.**

### 4-4. 뷰어만 독자가 직접 고른다

뷰어는 예외로 `body[data-theme]` 에 변수를 덮어써서 독자가 배경을 고른다.

```css
body[data-theme='sepia'] { --bg: …; --panel: …; --fg: …; --line: …; --muted: …; }
```
- 지원: `light` · `sepia` · `dark`
- 이 방식은 **읽기 화면 한정.** 다른 화면에 테마 선택기를 붙이지 않는다.
- 테마를 덮을 땐 **10개 축을 전부 다시 적는다.** 일부만 적으면 OS 다크모드와 섞여 깨진다.

### 4-5. 가변 치수도 변수로

독자가 조절하는 치수는 변수로 빼고 JS는 변수 값만 바꾼다.
```css
.bl-body { font-size: var(--reader-size, 16px); line-height: var(--reader-leading, 1.95); }
```
**폴백을 반드시 둔다.** JS가 죽어도 읽히게.

### 4-6. 이미지 자산은 파일을 갈아끼운다

**이미지는 CSS 변수를 못 쓴다.** 그러니 다크모드 대응을 `filter: invert()` 같은 꼼수로 하지 말고
**라이트용 · 다크용 파일을 각각 만들어** `<picture>` 로 고른다.

```html
<a class="bl-logo" href="/bltest/">
    <picture>
        <source srcset="/static/img/logo-dark.png" media="(prefers-color-scheme: dark)">
        <img src="/static/img/logo.png" alt="ARCApost">
    </picture>
</a>
```

- 크기는 **CSS 로만** 정한다 (`.bl-logo img { height: 26px; width: auto }`).
  `<img width>` 속성으로 박지 않는다 — 480px 미디어쿼리에서 못 줄인다.
- `display: block` 을 준다. 인라인 이미지의 baseline 여백 때문에 헤더 정렬이 틀어진다.
- **투명 배경 PNG** 로 만든다. 흰 배경이 박혀 있으면 다크모드에서 흰 사각형이 뜬다.
- 표시 크기의 **2~3배 해상도**까지만. 원본 마스터를 그대로 올리지 않는다 (5-2).
- `<picture>` 는 `prefers-color-scheme` 만 따라간다. **뷰어의 `data-theme` 은 못 따라가므로
  읽기 화면에 이미지 자산을 쓰지 않는다.**

---

## 5. 네이밍 · 파일 규약 (고정)

### 5-1. 클래스는 전부 `bl-` 접두사

다른 서비스 CSS와 충돌하지 않게 하기 위한 것이다. 전역 이름(`.card`, `.btn`, `.wrap`) 금지.

```
.bl-wrap  .bl-head  .bl-logo  .bl-spacer
.bl-btn   .bl-input .bl-textarea .bl-select .bl-field .bl-label .bl-help
.bl-list  .bl-card  .bl-badge .bl-tag  .bl-empty
.bl-hero  .bl-sec-title .bl-eps .bl-ep
.bl-reader .bl-body .bl-reader-bar
.bl-panel .bl-keybox .bl-notice
.bl-modal .bl-modal-box .bl-modal-actions
```

변형은 **접두사 없는 수식 클래스**를 덧붙인다:
`.bl-btn.primary` · `.bl-btn.danger` · `.bl-btn.small` · `.bl-badge.teen|mine|draft` · `.bl-notice.warn`

새 부품을 만들기 전에 위 목록에 쓸 게 있는지 먼저 본다. **부품을 늘리는 것보다 재사용이 우선.**

### 5-2. 파일 배치

```
templates/bl/<화면>.html      화면당 1개
static/css/bl.css             1개. 화면별로 쪼개지 않는다.
static/js/bl/<화면>.js        화면당 1개 (ES 모듈)
static/js/bl/card.js          화면 간 공용 조각은 별도 모듈로
static/js/bl/key.js
static/img/logo.png           웹에 나가는 자산 — 표시 크기의 2~3배까지만
static/img/logo-dark.png      다크모드용 (4-6)
assets/logo-master.png        원본 마스터. nginx 가 서빙하지 않는 곳에 둔다
```

`static/` 아래는 **nginx 가 그대로 서빙한다.** 고해상도 원본·작업 파일을 여기 두지 않는다.

### 5-3. `bl.css` 내부 순서

```
/* 파일 첫머리에 이 파일이 뭔지 1~3줄 주석 */
1. :root 변수 + 다크모드 변수
2. 전역 리셋 · body
3. .bl-wrap  (컨테이너)
4. 헤더
5. 버튼 · 입력
6. 목록 → 작품 상세 → 뷰어 → 작가 서재     ← 섹션 주석으로 구분
7. 모달
8. @media (max-width: 480px)               ← 항상 맨 끝
```
새 화면 스타일은 6번 블록 끝에 **새 섹션 주석과 함께** 추가한다.

### 5-4. 이름 — 브랜드명과 코드 식별자를 섞지 않는다

서비스명은 **알카포스트** 로 확정됐다. 다만 **코드의 `bl` 계열 식별자는 그대로 둔다.**

| 자리 | 쓴다 | 이유 |
|---|---|---|
| 화면에 보이는 글 (`<title>` · 안내문 · 본문) | 알카포스트 | 국문 서비스명 |
| 로고 이미지 · `alt` | ARCApost | 워드마크 철자 그대로 |
| 경로 `/bltest/` · `bl-` 접두사 · `bl.css` · `templates/bl/` | 그대로 | 링크가 깨지고 얻는 게 없다 |
| `OPEN_TEST_KEY` 값 | 그대로 | **DB에 저장된 기존 글의 작가 키다. 바꾸면 끝난다** |

프로토타입 · 테스트 중이라는 안내(`.bl-notice`)는 사실이므로 유지한다.

### 5-5. 기타

- 주석은 한국어. **"왜 이렇게 했는지"**를 적는다. 무엇을 하는지는 코드가 말한다.
- `[hidden] { display: none !important; }` 를 전역에 두고, 표시/숨김은 `hidden` 속성으로 제어한다.
- transition은 `border-color` · `transform` · `opacity` 정도로 짧게(`.15s`). 화려한 애니메이션 금지.
- 프로토타입 단계의 제약(로그인 없음 · 15세 이하만 등)은 `.bl-notice` 로 화면 상단에 명시한다.

---

## 6. 현재 값 스냅샷 — **잠정, 확정 아님**

> 아래는 지금 `bl.css` 에 들어 있는 값이다.
> **디자인이 바뀌면 여기 숫자만 갈아엎으면 되고, 1~5장은 그대로 간다.** 그게 이 구조의 목적이다.

**색 (라이트 / 다크)**

| 변수 | 라이트 | 다크 |
|---|---|---|
| `--bg` | `#ffffff` | `#0d0d0d` |
| `--panel` | `#ffffff` | `#0d0d0d` |
| `--tint` | `#f5f5f5` | `#1a1a1a` |
| `--line` | `#e5e5e5` | `#2e2e2e` |
| `--line-strong` | `#111111` | `#ededed` |
| `--fg` | `#111111` | `#ededed` |
| `--muted` | `#737373` | `#8f8f8f` |
| `--accent` | `#111111` | `#ededed` |
| `--accent-fg` | `#ffffff` | `#0d0d0d` |
| `--danger` | `#dc2626` | `#f87171` |

- `--bg` = `--panel` (순백/순흑). **카드·패널은 배경색이 아니라 `--line` 테두리로만 구분된다.**
- `--accent` = `--fg`. 강조는 색이 아니라 검정 채움(`.bl-btn.primary`)으로 만든다.
- `--line-strong` 은 hover에서 테두리를 **완전한 검정/흰색**으로 올린다. 테두리만으로 구분되는
  구조라 hover가 확실히 보여야 한다.
- 로고는 텍스트가 아니라 **이미지**다 (4-6). 팔레트 변수의 영향을 받지 않는다.

**뱃지** — `.teen`(15세) `--fg`+`--line-strong` · `.mine`(내 작품) `--accent` · `.draft`(비공개) `--danger`

**로고** — `480x144` (투명 PNG) · 헤더 표시 높이 `26px` (≤480px: `22px`)
원본 브랜드색 검정 `#201e1d` + 레드 `#e30613` / 다크 변형 `#ededed` + `#ff5c63`

**뷰어 sepia 테마** — `--bg`·`--panel` `#f4ecd8` / `--tint #eae0c8` / `--fg #433422` / `--line #ddd0b4` / `--muted #8a7a5f`

**치수**

| 항목 | 현재 값 |
|---|---|
| 컨테이너 폭 | `.bl-wrap 900` / `.bl-reader 720` / `.bl-modal-box 460` |
| 컨테이너 padding | `.bl-wrap 20px 18px 60px` (≤480px: `16px 14px 50px`) |
| | `.bl-reader 20px 20px 80px` (≤480px: `16px 16px 70px`) |
| 모서리 | 버튼·입력 `7px` · 카드/패널/목록 `11px` · 모달 `13px` · pill(뱃지·태그) `999px` |
| 간격 | 카드 사이 `12px` · 인라인 요소 `8px` · 툴바 입력 최소폭 `160px` |
| 글자 | 본문 `14px` · 메타/도움말 `12~12.5px` · 카드 제목 `16px` · 로고 `19px` · h1 `22px` |
| 행간 | 기본 `1.6` · 줄거리 `1.75` · 뷰어 본문 `1.95` |
| 폰트 | `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Malgun Gothic', sans-serif` |
| | 작가 키: `Consolas, 'Courier New', monospace` |
| hover | 카드 `translateY(-2px)` + 테두리 `--line-strong` · 주 버튼 `opacity .88` |

---

## 7. 새 화면 체크리스트

- [ ] `<meta name="viewport">` 있는가
- [ ] `.bl-wrap` (또는 `.bl-reader`) 로 감쌌는가 — 2-2 등급 중 하나를 골랐는가
- [ ] 헤더에 `.bl-logo` + `.bl-spacer` 패턴을 썼는가
- [ ] 가로 배치에 `flex-wrap: wrap` 걸었는가
- [ ] 늘어나는 입력에 `flex: 1` + `min-width` 있는가
- [ ] 길어질 수 있는 flex 자식에 `min-width: 0` 있는가
- [ ] 색을 hex로 하드코딩하지 않고 변수를 썼는가 (무채색만 — 빨강은 삭제·경고·비공개만)
- [ ] 면을 구분할 때 `--bg` 가 아니라 `--tint` 를 썼는가
- [ ] 이미지를 넣었다면 다크용 파일도 만들고 `<picture>` 로 걸었는가 (4-6)
- [ ] 새 부품을 만들기 전에 5-1 목록에서 재사용할 걸 찾아봤는가
- [ ] `bl.css` 의 정해진 자리(5-3)에 섹션 주석과 함께 넣었는가
- [ ] 480px 미디어쿼리를 새로 추가하지 않았는가
- [ ] 폰(360px) · 태블릿 · 와이드(1920px)에서 가로 스크롤이 없는가

---

## 8. 이 문서를 고치는 기준

| 상황 | 할 일 |
|---|---|
| 색·폭·모서리·글자 크기를 바꾼다 | **6장 표만 갱신.** 1~5장 손대지 않는다 |
| 컨테이너 폭 등급을 추가한다 | 2-2 표에 한 줄 추가 |
| 색 변수 축을 추가한다 | 4-1을 먼저 고치고 나서 CSS 수정 |
| 상태 색(초록·파랑 등)을 추가하고 싶다 | **4-2 모노톤 원칙을 먼저 고친다** |
| 공용 부품을 추가한다 | 5-1 목록에 등록 |
| 서비스명을 바꾼다 | **5-4 표대로 보이는 글만.** 경로·접두사·키 값은 건드리지 않는다 |
| 이미지 자산을 추가한다 | 4-6 대로 라이트/다크 2벌 + 마스터는 `assets/` |
| 멀티컬럼 · 사이드바 등 새 레이아웃 패턴이 필요하다 | **2장을 먼저 고친다.** 코드 먼저 짜지 않는다 |
