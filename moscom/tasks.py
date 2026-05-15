"""Celery 태스크 — 1시간마다 동기화."""
from celery import shared_task
from .sync import run_sync


@shared_task(name='moscom.sync_hourly')
def sync_hourly():
    return run_sync()
