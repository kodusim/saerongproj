# 배포 메모

## 구성

```
nginx (443/80)  →  uvicorn 127.0.0.1:8000  (systemd: saerong.service)
                   /static  → /srv/staticfiles     (nginx alias)
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

**워커는 1개로 고정한다.** 이유는 유닛 파일 주석 참고 — TDM 모델이 워커당 약
470MB 를 잡고, 채팅 WebSocket 브로드캐스트가 프로세스 내부에서 일어난다.
워커를 늘리려면 먼저 Redis pub/sub 같은 프로세스 간 브로드캐스트가 필요하다.

## nginx — WebSocket

채팅이 WebSocket 을 쓰므로 `location /` 블록에 업그레이드 헤더가 있어야 한다:

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
ssh saerong-instance "cd /srv/course-repo && sudo git pull \
  && sudo /srv/venv/bin/python -c 'import app.main' \
  && sudo systemctl restart saerong && sleep 2 && systemctl is-active saerong"
curl -sS -o /dev/null -w '%{http_code}\n' https://saerong.com/healthz
```

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
