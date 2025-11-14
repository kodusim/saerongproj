#!/bin/bash
# 긴급 메모리 부족 해결 스크립트

echo "=== 긴급 메모리 최적화 ==="

# 1. Celery 즉시 중지 (자동 크롤링 방지)
echo "[1] Celery 중지 중..."
sudo systemctl stop celery celery-beat
sudo pkill -9 -f 'celery.*saerong'
sudo pkill -9 -f 'chrome'
echo "✓ Celery 및 Chrome 프로세스 종료"

# 2. Swap 메모리 추가 (2GB)
echo -e "\n[2] Swap 메모리 추가 중..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "✓ 2GB Swap 메모리 추가 완료"
else
    sudo swapon /swapfile 2>/dev/null || echo "Swap 이미 활성화됨"
fi

# 3. Swap 사용률 조정 (메모리 부족 시에만 Swap 사용)
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf

# 4. 메모리 상태 확인
echo -e "\n[3] 현재 메모리 상태:"
free -h

# 5. DataSource 크롤링 간격 늘리기
echo -e "\n[4] 크롤링 간격 조정 중..."
cd /srv/course-repo
/srv/venv/bin/python3.12 -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saerong.settings')
django.setup()

from sources.models import DataSource

# 모든 DataSource의 크롤링 간격을 최소 60분으로 설정
sources = DataSource.objects.filter(crawl_interval__lt=60)
count = sources.count()
sources.update(crawl_interval=60)
print(f'✓ {count}개 DataSource의 크롤링 간격을 60분으로 변경')
"

# 6. Celery Beat 주기를 5분으로 변경 (1분 → 5분)
echo -e "\n[5] Celery Beat 주기 조정 중..."
cd /srv/course-repo
/srv/venv/bin/python3.12 -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saerong.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, IntervalSchedule

# 5분 간격 스케줄 생성
schedule, _ = IntervalSchedule.objects.get_or_create(
    every=5,
    period='minutes'
)

# crawl_all_sources 작업 업데이트
task = PeriodicTask.objects.filter(name='crawl_all_sources').first()
if task:
    task.interval = schedule
    task.save()
    print('✓ Celery Beat 주기를 5분으로 변경')
else:
    print('⚠ crawl_all_sources 작업을 찾을 수 없음')
"

# 7. Celery 재시작 (concurrency=1 유지)
echo -e "\n[6] Celery 재시작 중..."
sudo systemctl start celery celery-beat
sleep 3

# 8. 상태 확인
echo -e "\n[7] 최종 상태:"
echo "Celery Worker:"
sudo systemctl status celery --no-pager | grep -E 'Active|concurrency' | head -3
echo -e "\nCelery Beat:"
sudo systemctl status celery-beat --no-pager | grep Active
echo -e "\n메모리:"
free -h | grep -E 'Mem|Swap'

echo -e "\n=== 완료 ==="
echo "✅ Swap 메모리 2GB 추가"
echo "✅ 크롤링 간격 최소 60분"
echo "✅ Celery Beat 5분마다 체크 (1분→5분)"
echo "✅ Concurrency=1 유지"
echo ""
echo "⚠️  권장사항: 게임이 늘어나면 월별 \$12 (2GB) 플랜으로 업그레이드 필요"
