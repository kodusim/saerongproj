import os
from celery import Celery
from celery.schedules import crontab

# Django settings 모듈 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saerong.settings')

app = Celery('saerong')

# Django settings에서 CELERY로 시작하는 설정을 모두 가져옴
app.config_from_object('django.conf:settings', namespace='CELERY')

# Django 앱의 tasks.py를 자동으로 찾아서 등록
app.autodiscover_tasks()

# Celery Beat 스케줄 설정
# **주의: 이제 각 크롤링이 끝나면 자동으로 다음 크롤링을 예약합니다.**
# **주기적인 Beat 스케줄은 필요 없습니다.**
app.conf.beat_schedule = {
    # 기존 10분마다 크롤링 체크 방식 제거
    # 각 소스가 자신의 crawl_interval에 맞춰 자동으로 다음 크롤링을 예약함

    # MOSCOM 데이터 1시간마다 동기화 — 매시 05분
    'moscom-sync-hourly': {
        'task': 'moscom.sync_hourly',
        'schedule': crontab(minute='5'),
    },
    # AI 예측 모델 매일 새벽 5시 10분 재학습
    # (전날 야간 수집(18:00~05:00) 직후 — Collection sync 가 05:05에 끝났을 시점 다음)
    'moscom-retrain-daily': {
        'task': 'moscom.retrain_daily',
        'schedule': crontab(hour=5, minute=10),
    },
}

app.conf.timezone = 'Asia/Seoul'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
