# 배포 메모

## 구성

```
nginx (443/80)  →  uvicorn 127.0.0.1:8000  (systemd: saerong.service)
                   /static  → /srv/course-repo/static (실서버 nginx alias, 2026-09-29 확인)
                   /media   → /srv/course-repo/mediafiles (nginx alias)
PostgreSQL 14 (DB saerong)
```

프로젝트 경로 `/srv/course-repo`, 가상환경 `/srv/venv`.

## systemd

[saerong.service](saerong.service) 를 `/etc/systemd/system/` 에 두고:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now saerong
sudo systemctl status saerong
```

**워커는 1개를 유지한다.** TDM 모델이 워커당 약 470MB를 사용하므로 변경 전 메모리 예산을 확인한다. Work·농사 게임 HTTP/WebSocket 라우터는 현재 해제했다. 기존 데이터와 업로드는 보존한다.

## nginx — WebSocket

아래는 기존 WebSocket 프록시 구성 참고다. 현재 Work 채팅은 공개하지 않으며, 이번 홈 배포에서는 nginx 설정을 바꾸지 않는다.

```nginx
location / {
    proxy_pass http://saerong_app;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 3600s;
}
```

`http` 블록에 다음이 필요하다:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}
```

## 배포

```bash
git push origin main
ssh saerong-instance "cd /srv/course-repo && sudo git pull --ff-only \
  && sudo /srv/venv/bin/python -c 'import app.main' \
  && sudo systemctl restart saerong && sleep 2 && systemctl is-active saerong"
curl -sS -o /dev/null -w '%{http_code}\n' https://saerong.com/healthz
```

Windows에서 SSH 별칭의 키 경로가 맞지 않으면 세션에서 확인한 키 파일을 `ssh -i`로 명시한다. 배포 전 DNS·서버 저장소 상태·실제 nginx alias·현재 커밋을 확인한다. 이번 홈 변경은 의존성 설치나 DB 마이그레이션이 필요 없다. 새 HTML과 `/static/css/landing.css?v=4`, `/static/js/landing.js?v=4`의 응답, `/tdm/` 인증 리디렉션, `/tdmprediction/*` 308, `/work/` 404를 확인한다.

## DB 마이그레이션

기존 테이블은 Django 가 만든 것이라 baseline 리비전을 **실행하지 않고 기록만** 했다:

```bash
sudo /srv/venv/bin/alembic stamp 0001     # 최초 1회 (이미 완료)
sudo /srv/venv/bin/alembic upgrade head   # 이후 변경 적용
```

## 모델 가중치

`ml_artifacts/` 는 용량 때문에 git 에서 제외한다. 서버에 직접 올린다:

```bash
scp ml_artifacts/random_forest.joblib saerong-instance:/srv/course-repo/ml_artifacts/
```

torch 는 CPU 빌드로:

```bash
sudo /srv/venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch==2.7.0
```
