"""moscom 동기화 management command.

사용법:
  python manage.py moscom_sync                 # 장비 + 포집 incremental
  python manage.py moscom_sync --backfill 30   # 30일 백필 (포집)
  python manage.py moscom_sync --devices-only  # 장비만
"""
import json
from django.core.management.base import BaseCommand

from moscom.sync import sync_devices, sync_collections, backfill_collections, run_sync


class Command(BaseCommand):
    help = 'MOSCOM API → 로컬 DB 동기화'

    def add_arguments(self, parser):
        parser.add_argument('--backfill', type=int, default=0, help='포집 백필 일수 (기본 0)')
        parser.add_argument('--devices-only', action='store_true', help='장비만 동기화')
        parser.add_argument('--collections-only', action='store_true', help='포집만 동기화')

    def handle(self, *args, **opts):
        if opts['backfill'] > 0:
            self.stdout.write(f'Backfilling {opts["backfill"]} days of collections...')
            r = backfill_collections(days=opts['backfill'])
            self.stdout.write(self.style.SUCCESS(f'backfill: {json.dumps(r, ensure_ascii=False)}'))
            return
        if opts['devices_only']:
            r = sync_devices()
            self.stdout.write(self.style.SUCCESS(f'devices: {json.dumps(r, ensure_ascii=False)}'))
            return
        if opts['collections_only']:
            r = sync_collections()
            self.stdout.write(self.style.SUCCESS(f'collections: {json.dumps(r, ensure_ascii=False)}'))
            return
        # default: 둘 다
        r = run_sync()
        self.stdout.write(self.style.SUCCESS(f'sync: {json.dumps(r, ensure_ascii=False)}'))
