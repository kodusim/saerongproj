#!/bin/bash
# Celery 동시 실행 수를 1로 제한하여 메모리 초과 방지

echo "=== Celery Concurrency 설정 ==="

# 1. Celery worker 설정 확인
echo -e "\n[1] 현재 실행 중인 Celery 프로세스:"
ps aux | grep celery | grep -v grep

# 2. systemd 서비스 파일 확인
echo -e "\n[2] Celery 서비스 파일 확인:"
if [ -f /etc/systemd/system/celery.service ]; then
    echo "파일 위치: /etc/systemd/system/celery.service"
    grep "ExecStart" /etc/systemd/system/celery.service
else
    echo "systemd 서비스 파일 없음"
fi

# 3. Celery worker 서비스 파일 수정
echo -e "\n[3] Celery worker 설정 수정 중..."

# /etc/systemd/system/celery.service 파일 수정
sudo tee /etc/systemd/system/celery.service > /dev/null <<'EOF'
[Unit]
Description=Celery Service
After=network.target

[Service]
Type=forking
User=ubuntu
Group=ubuntu
WorkingDirectory=/srv/course-repo
Environment="PATH=/srv/venv/bin"
ExecStart=/srv/venv/bin/celery -A saerong worker \
    --loglevel=info \
    --logfile=/var/log/celery/worker.log \
    --pidfile=/var/run/celery/worker.pid \
    --concurrency=1 \
    --max-tasks-per-child=10 \
    --time-limit=300 \
    --soft-time-limit=240
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Celery worker 설정 완료"
echo "  - concurrency=1: 한 번에 1개씩만 실행"
echo "  - max-tasks-per-child=10: 10개 작업 후 worker 재시작 (메모리 누수 방지)"
echo "  - time-limit=300: 5분 초과 시 강제 종료"
echo "  - soft-time-limit=240: 4분 후 경고"

# 4. Celery beat 서비스도 확인/수정
echo -e "\n[4] Celery beat 설정 확인..."
if [ ! -f /etc/systemd/system/celery-beat.service ]; then
    echo "Celery beat 서비스 파일 생성 중..."
    sudo tee /etc/systemd/system/celery-beat.service > /dev/null <<'EOF'
[Unit]
Description=Celery Beat Service
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/srv/course-repo
Environment="PATH=/srv/venv/bin"
ExecStart=/srv/venv/bin/celery -A saerong beat \
    --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --logfile=/var/log/celery/beat.log \
    --pidfile=/var/run/celery/beat.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    echo "✓ Celery beat 서비스 파일 생성 완료"
fi

# 5. 로그 디렉토리 생성
echo -e "\n[5] 로그 디렉토리 확인..."
sudo mkdir -p /var/log/celery /var/run/celery
sudo chown -R ubuntu:ubuntu /var/log/celery /var/run/celery
echo "✓ 로그 디렉토리 생성 완료"

# 6. systemd 리로드 및 서비스 재시작
echo -e "\n[6] 서비스 재시작 중..."
sudo systemctl daemon-reload
sudo systemctl restart celery celery-beat
sudo systemctl enable celery celery-beat

# 7. 상태 확인
echo -e "\n[7] 서비스 상태 확인:"
sudo systemctl status celery --no-pager | head -15
sudo systemctl status celery-beat --no-pager | head -15

echo -e "\n=== 완료 ==="
echo "Celery worker는 이제 한 번에 1개씩만 작업을 처리합니다."
echo "메모리 부족으로 인한 서버 다운이 방지됩니다."
