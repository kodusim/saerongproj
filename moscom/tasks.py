"""Celery 태스크 — 1시간마다 동기화, 매일 새벽 5시 재학습."""
import logging
from celery import shared_task
from .sync import run_sync

logger = logging.getLogger(__name__)


@shared_task(name='moscom.sync_hourly')
def sync_hourly():
    return run_sync()


@shared_task(name='moscom.retrain_daily')
def retrain_daily():
    """매일 새벽 5시 — 어제까지 들어온 데이터로 AI 모델 재학습.
    Celery 가 worker 안에서 management command 호출."""
    from django.core.management import call_command
    from io import StringIO
    buf = StringIO()
    try:
        call_command('moscom_train', stdout=buf)
        # predictor lru_cache 무효화
        from core import predictor
        try:
            predictor._load.cache_clear()
        except Exception:
            pass
        return {'ok': True, 'stdout_tail': buf.getvalue()[-2000:]}
    except Exception as e:
        logger.exception('retrain_daily failed')
        return {'ok': False, 'error': str(e), 'stdout': buf.getvalue()[-2000:]}
