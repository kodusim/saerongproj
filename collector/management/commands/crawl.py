from django.core.management.base import BaseCommand
from sources.models import DataSource
from collector.tasks import crawl_data_source


class Command(BaseCommand):
    help = '데이터 소스를 크롤링합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source-id',
            type=int,
            help='크롤링할 데이터 소스 ID'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='모든 활성화된 데이터 소스 크롤링'
        )

    def handle(self, *args, **options):
        if options['all']:
            sources = DataSource.objects.filter(is_active=True)
            self.stdout.write(f"크롤링할 데이터 소스: {sources.count()}개")

            for source in sources:
                self.stdout.write(f"\n크롤링 중: {source.name}")
                try:
                    result = crawl_data_source(source.id)
                    self.stdout.write(self.style.SUCCESS(f"[OK] {result}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"[ERROR] 실패: {str(e)}"))

        elif options['source_id']:
            source_id = options['source_id']
            try:
                source = DataSource.objects.get(id=source_id)
                self.stdout.write(f"크롤링 중: {source.name}")

                result = crawl_data_source(source_id)
                self.stdout.write(self.style.SUCCESS(f"[OK] {result}"))

            except DataSource.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"데이터 소스를 찾을 수 없습니다: ID {source_id}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[ERROR] 실패: {str(e)}"))

        else:
            self.stdout.write(self.style.WARNING("--source-id 또는 --all 옵션을 사용하세요"))
            self.stdout.write("\n사용 가능한 데이터 소스:")
            for source in DataSource.objects.filter(is_active=True):
                self.stdout.write(f"  ID {source.id}: {source.name}")
