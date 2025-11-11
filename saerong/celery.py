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
app.conf.beat_schedule = {
    'crawl-all-sources-every-10-minutes': {
        'task': 'collector.tasks.crawl_all_sources',
        'schedule': 600.0,  # 10분마다 (초 단위)
    },
    # 추가 예시: 매일 새벽 2시에 전체 크롤링
    # 'crawl-all-sources-daily': {
    #     'task': 'collector.tasks.crawl_all_sources',
    #     'schedule': crontab(hour=2, minute=0),
    # },
}

app.conf.timezone = 'Asia/Seoul'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
