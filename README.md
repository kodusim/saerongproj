# saerongproj

saerong.com 을 서빙하는 **FastAPI** 애플리케이션. 두 개의 독립적인 기능만 있다.

| 경로 | 내용 |
|---|---|
| `/` | 랜딩 |
| `/tdmprediction/` | 반코마이신 혈중 농도 하이브리드(ML + DL) 예측 |
| `/tdmprediction/logs/` | 예측 감사 로그 (읽기 전용) |
| `/work/` | 실시간 채팅 · 구글 스칼라 검색 · 게시판 |
| `/healthz` | 헬스체크 |

## 구성

- FastAPI + uvicorn (ASGI), Jinja2 템플릿
- SQLAlchemy 2.0 (async, asyncpg) + Alembic, PostgreSQL 14
- 세션: 서명된 쿠키 (Starlette `SessionMiddleware`)
- CSRF: `csrftoken` 쿠키 + `X-CSRFToken` 헤더 double-submit
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
  services/predictor.py  TDM 추론 (ML joblib + LSTM .pt)
  services/scholar.py    구글 스칼라 스크래핑 (async httpx)
  services/storage.py    업로드 이미지 저장
migrations/            Alembic
templates/, static/
ml_artifacts/          모델 가중치 (git 제외 — 서버에 직접 업로드)
deploy/                systemd 유닛 + 배포 메모
```

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
