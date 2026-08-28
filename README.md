# saerongproj

saerong.com 을 서빙하는 **FastAPI** 애플리케이션. 두 개의 독립적인 기능만 있다.

| 경로 | 내용 |
|---|---|
| `/` | 랜딩 |
| `/tdmprediction/` | 반코마이신 혈중 농도 하이브리드(ML + DL) 예측 |
| `/tdmprediction/logs/` | 예측 감사 로그 (읽기 전용) |
| `/work/` | 실시간 채팅 · 자료실 · 공지사항 · 일정 달력 · 미니게임 |
| `/bltest/` | **알카포스트** — BL 소설 연재 플랫폼 (프로토타입) — [기획](LB기획.md) · [디자인 규약](DESIGN.md) |
| `/healthz` | 헬스체크 |

## 구성

- FastAPI + uvicorn (ASGI), Jinja2 템플릿
- SQLAlchemy 2.0 (async, asyncpg) + Alembic, PostgreSQL 14
- 세션: 서명된 쿠키 (Starlette `SessionMiddleware`)
- CSRF: `csrftoken` 쿠키 + `X-CSRFToken` 헤더 double-submit
- 프런트: 빌드 도구 없음 — 순수 ES 모듈 + CSS 를 nginx 가 그대로 서빙
- 채팅: WebSocket (`/work/ws`), 끊기면 폴링으로 자동 강등
- 운영: nginx → uvicorn 127.0.0.1:8000, `/srv/course-repo`, venv `/srv/venv`

```
app/
  main.py              FastAPI 앱, 미들웨어, 라우터 등록
  config.py            pydantic-settings (.env 를 읽는다)
  db.py                async 엔진 / 세션
  models.py            기존 테이블에 그대로 매핑
  security.py          세션 인증 + CSRF
  templating.py        Jinja2
  routers/tdm.py       /tdmprediction
  routers/work.py      /work
  routers/farm.py      /work/api/farm (농사 게임)
  services/predictor.py  TDM 추론 (ML joblib + LSTM .pt)
  services/storage.py    업로드 이미지 저장
  services/farm.py       농사 게임 규칙 (작물·건물·성장 판정)
  ws.py                  채팅 WebSocket 허브 (프로세스 내 브로드캐스트)
migrations/            Alembic
templates/             마크업만 (CSS/JS 는 static/)
static/css/            work-base · groupware · vscode · games · tdm-*
static/js/lib/         dom.js (헬퍼) · api.js (CSRF 붙이는 fetch 래퍼)
static/js/work/        main(엔트리) · state(공유 상태+구독) · chat
                       board(자료실·공지 공용 팩토리) · schedule(월 달력)
                       games/(미니게임 7종, stardew 는 캔버스)
                       theme · nav · unread · lightbox
static/js/tdm/         predict.js
ml_artifacts/          모델 가중치 (git 제외 — 서버에 직접 업로드)
deploy/                systemd 유닛 · nginx 설정 · 배포 메모
```

프런트는 빌드 단계가 없다. `<script type="module">` 로 바로 불러오므로 **인라인
`onclick` 을 쓸 수 없다** (모듈 스코프는 전역에 노출되지 않는다) — 이벤트는 모듈
안에서 `addEventListener` 로 바인딩한다.

`/work` 은 그룹웨어 / VS Code 두 테마의 DOM 을 모두 문서에 두고 한쪽만 보여준다.
상태는 `static/js/work/state.js` 에 한 벌만 있고 테마별 DOM 두 벌에 같은 내용을
렌더링한다 — 그래서 테마를 바꿔도 보고 있던 화면과 내용이 유지된다.

DB 테이블은 Django 시절 이름(`tdm_predictionlog`, `work_workchatmessage`,
`work_workpost`)을 그대로 쓴다 — 데이터를 그대로 이어받기 위해 바꾸지 않았다.

## 설치

```bash
python -m venv venv && . venv/bin/activate
pip install -r requirements.txt        # prod
pip install -r requirements/dev.txt    # dev
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.7.0
```

## 실행

```bash
uvicorn app.main:app --reload           # DEBUG=True 면 /api/docs 도 열린다
```

## 배포

[deploy/README.md](deploy/README.md) 참고.

## 삭제된 것들

과거에 있었으나 제거된 앱 — 필요하면 git 히스토리에서 복구한다.
DB 테이블은 drop 하지 않고 남겨두었다.

- `animal` (2026-06-08)
- `moscom` / `/mosquito-test/` (2026-08-24) — moscom.ai 는 별도 서버·별도 저장소로 이전
- `common`, `core`, `sources`, `collector`, `analytics`, `api`, `game_honey_alarm` (2026-08-24)
- Django 자체 (2026-08-24) — FastAPI 로 이전
