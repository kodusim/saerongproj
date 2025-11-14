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
}

app.conf.timezone = 'Asia/Seoul'


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
