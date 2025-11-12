from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
from sources.models import DataSource
from collector.models import CollectedData, CrawlLog
from collector.crawlers import MapleStoryCrawler, GenericSeleniumCrawler, GenericRequestsCrawler
import importlib


@shared_task
def crawl_data_source(source_id):
    """특정 데이터 소스를 크롤링하는 Task"""

    start_time = timezone.now()

    try:
        # 데이터 소스 가져오기
        source = DataSource.objects.get(id=source_id, is_active=True)

        # 크롤러 클래스 가져오기 (자동 선택 지원)
        crawler_class = get_crawler_class(source)
        if not crawler_class:
            raise Exception(f"Crawler class not found for source: {source.name}")

        # 크롤러 실행
        crawler = crawler_class(source)
        items = crawler.crawl()

        # 데이터 저장
        new_count = 0
        for item in items:
            hash_key = item.pop('hash_key')

            # 중복 체크
            if not CollectedData.objects.filter(hash_key=hash_key).exists():
                CollectedData.objects.create(
                    source=source,
                    data=item,
                    hash_key=hash_key
                )
                new_count += 1

        # 마지막 크롤링 시간 업데이트
        source.last_crawled_at = timezone.now()
        source.save()

        # 성공 로그 저장
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        CrawlLog.objects.create(
            source=source,
            status='success',
            items_collected=new_count,
            started_at=start_time,
            completed_at=end_time,
            duration_seconds=duration
        )

        return f"Crawled {new_count} new items from {source.name}"

    except Exception as e:
        # 실패 로그 저장
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        try:
            CrawlLog.objects.create(
                source=source,
                status='failed',
                items_collected=0,
                error_message=str(e),
                started_at=start_time,
                completed_at=end_time,
                duration_seconds=duration
            )
        except:
            pass

        raise


@shared_task
def crawl_all_sources():
    """모든 활성화된 데이터 소스를 크롤링"""
    sources = DataSource.objects.filter(is_active=True)

    for source in sources:
        crawl_data_source.delay(source.id)

    return f"Scheduled crawling for {sources.count()} sources"


def get_crawler_class(source):
    """
    DataSource 객체에서 적절한 크롤러 클래스 반환

    crawler_class가 지정되어 있으면 해당 클래스 사용
    없으면 crawler_type에 따라 자동으로 제네릭 크롤러 선택
    """

    # crawler_class가 지정된 경우 - 기존 로직 사용
    if source.crawler_class:
        crawler_path = source.crawler_class

        # 기본 크롤러 매핑
        crawler_map = {
            'collector.crawlers.game_crawlers.MapleStoryCrawler': MapleStoryCrawler,
            'MapleStoryCrawler': MapleStoryCrawler,
            'collector.crawlers.game_crawlers.GenericSeleniumCrawler': GenericSeleniumCrawler,
            'GenericSeleniumCrawler': GenericSeleniumCrawler,
            'collector.crawlers.game_crawlers.GenericRequestsCrawler': GenericRequestsCrawler,
            'GenericRequestsCrawler': GenericRequestsCrawler,
        }

        if crawler_path in crawler_map:
            return crawler_map[crawler_path]

        # 동적 import 시도
        try:
            module_path, class_name = crawler_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except Exception:
            return None

    # crawler_class가 없으면 crawler_type에 따라 자동 선택
    crawler_type = source.crawler_type

    if crawler_type == 'selenium':
        return GenericSeleniumCrawler
    elif crawler_type == 'beautifulsoup':
        return GenericRequestsCrawler
    elif crawler_type == 'api':
        raise NotImplementedError(
            "API 크롤러는 아직 구현되지 않았습니다. "
            "crawler_class를 직접 지정해주세요."
        )
    elif crawler_type == 'rss':
        raise NotImplementedError(
            "RSS 크롤러는 아직 구현되지 않았습니다. "
            "crawler_class를 직접 지정해주세요."
        )
    else:
        return None
