# BL 소설 플랫폼 기획 (`/bltest`)

작가가 작품을 연재하고 독자가 읽는 소설 플랫폼. saerong.com 안에 `/bltest`
경로로 붙인다.

작성 2026-08-26.

## 0. 전제와 제약

기획 단계에서 먼저 못박고 가는 것들:

- **유료화는 계정 없이 불가능하다.** IP 에게 회차를 팔 수 없다 — 구매 이력을
  붙일 주체가 없고, 기기를 바꾸면 산 것을 복원할 수 없고, 작가에게 정산할
  대상을 특정할 수 없다. 따라서 유료화는 계정 도입 **이후** 단계에 놓는다.
- **인증이 없는 동안 성인 등급은 열지 않는다.** 연령을 확인할 수단이 없기
  때문이다. 1차 프로토타입은 전체이용가 전제로 만든다.
- 지금 사이트는 인증이 전혀 없다. `work_*` 테이블은 전부 `author_ip` 기반이다.
  이 방식을 소설 플랫폼에 그대로 쓰면 **작가가 작품을 잃는다** (공유기 재접속,
  모바일 전환). 1차부터 IP 대신 작가 키를 쓴다 — 아래 참고.

## 1. 단계 구분

| 단계 | 범위 | 성인 등급 | 유료화 |
|---|---|---|---|
| 1차 | 인증 없는 프로토타입 (작가 키) | ✗ | ✗ |
| 2차 | 계정 + 연령 게이트 + 독자 상호작용 | ○ | ✗ |
| 3차 | 포인트 · 편당 결제 · 작가 정산 | ○ | ○ |

각 단계는 앞 단계 위에 얹는다. 1차 스키마에 2·3차용 컬럼 자리를 미리 만들어
두어 마이그레이션 비용을 낮춘다.

---

## 2. 1차 — 인증 없는 프로토타입

### 작가 키 (author_key)

최초 글쓰기 때 랜덤 토큰을 발급해 `localStorage` 에 저장한다. 이 토큰이
"이 작품은 내 것"의 근거가 된다. IP 보다 나은 점:

- 공유기 재접속 · 모바일 전환에도 작품을 잃지 않는다
- 키를 복사해두면 다른 기기에서도 이어서 쓸 수 있다
- 계정이 생기면 `author_key → user_id` 로 그대로 승계할 수 있다

키를 잃으면 작품 수정 권한도 잃는다. 발급 시 "이 키를 따로 보관하라"고
명확히 안내하고, 대시보드에서 언제든 다시 볼 수 있게 한다.

### 스키마

테이블 이름은 기존 규칙(`<app>_<model>`)을 따라 `bl_` 접두사를 쓴다.

```
bl_series                              작품
  id              BigInteger PK
  author_key      String(64)  index    작가 키
  author_name     String(32)           필명
  title           String(200)
  summary         Text                 소개
  tags            JSONB                ['현대물', '해피엔딩', ...]
  rating          String(8)            'all' | 'teen' | 'adult'
  status          String(16)           'ongoing' | 'done' | 'hiatus'
  views           Integer
  created_at / updated_at
  author_user_id  BigInteger NULL      ← 2차용 자리

bl_episode                             회차
  id              BigInteger PK
  series_id       FK → bl_series
  no              Integer              회차 번호
  title           String(200)
  body            Text
  published_at    DateTime NULL        NULL = 임시저장
  views           Integer
  created_at / updated_at
  is_free         Boolean default true ← 3차용 자리
  price           Integer default 0    ← 3차용 자리
  UNIQUE(series_id, no)

bl_report                              신고
  id              BigInteger PK
  target_type     String(16)           'series' | 'episode'
  target_id       BigInteger
  reason          String(32)           사유 코드
  detail          Text
  reporter_ip     INET
  status          String(16)           'open' | 'closed'
  created_at
```

`is_free` / `price` / `author_user_id` 를 1차에 미리 넣어두면 3차에서 대규모
마이그레이션을 피할 수 있다.

### 화면

```
/bltest/                  홈 — 신작 · 인기 · 태그별
/bltest/s/{id}            작품 소개 + 회차 목록
/bltest/s/{id}/{no}       뷰어 (글자 크기 · 다크모드 · 다음 화)
/bltest/write             작가 대시보드 (작품 · 회차 관리)
/bltest/write/{id}/new    회차 에디터
/bltest/admin/reports     신고 처리 큐
```

프런트는 기존 규칙을 따른다 — 빌드 도구 없이 순수 ES 모듈 + CSS,
`static/js/bl/`, `static/css/bl-*.css`. 인라인 `onclick` 금지.

### 뷰어

읽는 경험이 이 사이트의 본체다. 최소한 이것들은 1차에 넣는다:

- 글자 크기 · 줄간격 · 배경(밝게/어둡게) 조절, `localStorage` 저장
- 이전 화 / 다음 화 이동, 목록으로
- 읽던 위치 기억 (스크롤 비율)

---

## 3. 2차 — 계정과 연령 게이트

```
bl_user
  id, login_id, password_hash, nickname,
  birth_date        연령 확인용
  role              'reader' | 'author' | 'admin'
  created_at

bl_bookmark         유저 × 작품 (관심작품)
bl_comment          회차 댓글
```

계정이 생기고 나서야 성인 등급을 개방한다.

### 연령 게이트

- 작품 등록 시 **등급 지정을 필수**로 한다 (전체 / 15세 / 성인)
- 성인 작품은 로그인 + 생년 확인을 통과해야 본문을 연다.
  비로그인에게는 목록에서 제목만 보이고 본문·표지는 가린다
- 작가가 **키워드 경고 태그**를 다는 칸을 둔다 (독자가 지뢰를 피할 수 있게)

### 콘텐츠 정책 (이용약관에 명시)

UGC 플랫폼이므로 금지 항목을 처음부터 못박고, 신고 → 검토 → 조치 경로를
만들어 둔다. 최소한 다음은 등록 자체를 금지한다:

- **미성년자(또는 미성년으로 보이는 인물)에 대한 성적 묘사** — 법적으로도
  금지 대상이다. 발견 시 즉시 삭제 · 계정 정지
- 실존 인물을 특정한 성적 묘사
- 타인의 저작물 무단 게시

성폭력 등 범죄 소재를 다루는 창작물 자체는 허용하되, 등급과 경고 태그를
반드시 달게 하고 미성년자에게 노출되지 않도록 막는다.

### 운영 도구

- 신고 큐: 대상 미리보기 → 조치(무시 / 비공개 / 삭제 / 계정정지)
- 조치 이력 로그 (누가 언제 무엇을)

---

## 4. 3차 — 유료화

```
bl_wallet         유저별 포인트 잔액
bl_point_tx       충전 · 사용 · 환불 원장
bl_purchase       유저 × 회차 구매 기록 (재열람 무료)
bl_settlement     작가별 정산 (수익 배분율, 지급 상태)
```

**포인트는 반드시 원장(ledger) 방식으로 짠다.** 잔액 컬럼만 두고 더하고 빼면
분쟁이 났을 때 복원할 수 없다. `bl_point_tx` 에 모든 증감을 남기고 잔액은
그 합으로 검증한다.

### 판매 모델

- 편당 결제 (무료 회차 + 유료 회차 혼합)
- "기다리면 무료" — 일정 시간 경과 후 자동 무료 전환. 국내 표준 모델

### 결제 연동

포트원(구 아임포트) 또는 토스페이먼츠. 웹훅으로 결제 확정을 받아 포인트를
지급하고, 클라이언트 응답만 믿지 않는다.

### 개발보다 무거운 것 — 서류

3차는 코드보다 행정이 크다. 착수 전에 확인할 것:

- **통신판매업 신고** (관할 구청)
- **전자상거래법** 표시 의무 — 사업자 정보, 청약철회·환불 규정 고지
- **작가 정산 시 원천징수** — 사업소득 3.3%. 지급명세서 제출 의무
- 성인물 유통 시 **청소년유해매체물 표시 의무** (정보통신망법)

---

## 5. 구현 순서

1. `bl_series` / `bl_episode` / `bl_report` 모델 + Alembic 마이그레이션
2. `app/routers/bl.py` — 작품 · 회차 CRUD API
3. 목록 · 작품 · 뷰어 화면
4. 작가 대시보드 (작가 키 발급 · 에디터 · 임시저장)
5. 신고 버튼 + 관리 큐
6. (2차) 계정 · 연령 게이트 · 댓글 · 북마크
7. (3차) 포인트 · 결제 · 정산
