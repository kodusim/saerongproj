# saerongproj

saerong.com 을 서빙하는 Django 프로젝트. 현재 두 개의 독립적인 앱만 남아 있다.

| 경로 | 앱 | 내용 |
|---|---|---|
| `/` | — | 랜딩 (`templates/landing.html`) |
| `/tdmprediction/` | `tdm` | 반코마이신 혈중 농도 하이브리드(ML + DL) 예측 |
| `/work/` | `work` | 실시간 채팅 · 구글 스칼라 검색 · 게시판 |
| `/admin/` | — | Django 관리자 |

`tdm` 과 `work` 는 서로를, 그리고 다른 앱을 전혀 참조하지 않는다.

## 구성

- Python / Django 4.2, PostgreSQL
- 운영: gunicorn (systemd) + nginx, `/srv/course-repo`, venv `/srv/venv`
- `tdm` 모델 가중치는 `tdm/ml_artifacts/` — 용량 때문에 git 에서 제외(`.gitignore`)하고 서버에 직접 업로드한다.

## 설치

```bash
pip install -r requirements.txt        # prod
pip install -r requirements/dev.txt    # dev
```

torch 는 CPU 빌드로 따로 설치한다:

```bash
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.7.0
```

## 배포

```bash
git push origin main
ssh saerong-instance "cd /srv/course-repo && sudo git pull \
  && sudo /srv/venv/bin/python manage.py check \
  && sudo systemctl restart gunicorn"
```

## 삭제된 것들

과거에 이 저장소에 있었으나 제거된 앱 — 필요하면 git 히스토리에서 복구한다.
DB 테이블은 drop 하지 않고 남겨두었다.

- `animal` (2026-06-08)
- `moscom` / `/mosquito-test/` (2026-08-24) — moscom.ai 는 별도 서버·별도 저장소로 이전
- `common`, `core`, `sources`, `collector`, `analytics`, `api`, `game_honey_alarm` (2026-08-24)
