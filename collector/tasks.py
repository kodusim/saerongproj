from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
from sources.models import DataSource
from collector.models import CollectedData, CrawlLog
from collector.crawlers import MapleStoryCrawler, GenericSeleniumCrawler, GenericRequestsCrawler, NaverGameCrawler
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

        # 데이터 저장 (역순으로 저장하여 최신 항목이 가장 최근 collected_at을 갖도록 함)
        new_count = 0
        current_urls = set()  # 현재 크롤링된 URL들 수집

        for item in reversed(items):
            hash_key = item.pop('hash_key')
            current_urls.add(item.get('url', ''))

            # 중복 체크
            if not CollectedData.objects.filter(hash_key=hash_key).exists():
                collected_data = CollectedData.objects.create(
                    source=source,
                    data=item,
                    hash_key=hash_key
                )
                new_count += 1

                # 새 데이터 생성 시 구독자들에게 푸시 알림 발송
                try:
                    from api.push_notifications import notify_subscribers
                    notify_subscribers(collected_data)
                except Exception as e:
                    # 푸시 알림 실패해도 크롤링은 계속 진행
                    print(f"Failed to send push notification: {e}")

        # 삭제된 게시글 정리 (원본 사이트에서 삭제된 게시글 제거)
        deleted_count = cleanup_deleted_posts(source, current_urls)

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

        # 다음 크롤링 자동 예약 (crawl_interval 분 후)
        crawl_data_source.apply_async(
            (source_id,),
            countdown=source.crawl_interval * 60  # 분 → 초 변환
        )

        result_msg = f"Crawled {new_count} new items from {source.name}"
        if deleted_count > 0:
            result_msg += f", deleted {deleted_count} old items"
        return result_msg

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

            # 실패해도 다음 크롤링 예약 (30분 후 재시도)
            retry_interval = 30  # 분
            crawl_data_source.apply_async(
                (source_id,),
                countdown=retry_interval * 60
            )
        except:
            pass

        raise


@shared_task
def crawl_all_sources():
    """
    모든 활성화된 데이터 소스를 크롤링
    각 소스의 crawl_interval 설정에 따라 크롤링 시간이 된 것만 실행

    **이 함수는 더 이상 주기적으로 실행되지 않습니다.**
    **각 크롤링이 끝나면 자동으로 다음 크롤링을 예약합니다.**
    **이 함수는 수동 실행용 또는 초기 크롤링 시작용으로만 사용됩니다.**
    """
    sources = DataSource.objects.filter(is_active=True)

    crawled_count = 0
    for source in sources:
        # 마지막 크롤링 시간 확인
        if source.last_crawled_at is None:
            # 한 번도 크롤링 안 했으면 바로 실행
            crawl_data_source.delay(source.id)
            crawled_count += 1
        else:
            # 마지막 크롤링으로부터 설정된 시간이 지났는지 확인
            time_since_last_crawl = timezone.now() - source.last_crawled_at
            minutes_since_last_crawl = time_since_last_crawl.total_seconds() / 60

            if minutes_since_last_crawl >= source.crawl_interval:
                crawl_data_source.delay(source.id)
                crawled_count += 1

    return f"Scheduled crawling for {crawled_count}/{sources.count()} sources"


@shared_task
def start_all_crawlers():
    """
    모든 활성화된 데이터 소스의 크롤링 체인을 시작
    서버 재시작 후 또는 새 소스 추가 시 사용
    """
    sources = DataSource.objects.filter(is_active=True)

    for source in sources:
        # 각 소스의 크롤링을 즉시 시작 (자동으로 다음 크롤링도 예약됨)
        crawl_data_source.delay(source.id)

    return f"Started crawling chain for {sources.count()} sources"


def get_crawler_class(source):
    """
    DataSource 객체에서 적절한 크롤러 클래스 반환

    crawler_class가 지정되어 있으면 해당 클래스 사용
    없으면 crawler_type에 따라 자동으로 제네릭 크롤러 선택
    """

    # crawler_class가 지정된 경우 - 기존 로직 사용
    if source.crawler_class and source.crawler_class.strip():
        crawler_path = source.crawler_class

        # 기본 크롤러 매핑
        crawler_map = {
            'collector.crawlers.game_crawlers.MapleStoryCrawler': MapleStoryCrawler,
            'MapleStoryCrawler': MapleStoryCrawler,
            'collector.crawlers.game_crawlers.GenericSeleniumCrawler': GenericSeleniumCrawler,
            'GenericSeleniumCrawler': GenericSeleniumCrawler,
            'collector.crawlers.game_crawlers.GenericRequestsCrawler': GenericRequestsCrawler,
            'GenericRequestsCrawler': GenericRequestsCrawler,
            'collector.crawlers.game_crawlers.NaverGameCrawler': NaverGameCrawler,
            'NaverGameCrawler': NaverGameCrawler,
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


def cleanup_deleted_posts(source, current_urls):
    """
    원본 사이트에서 삭제된 게시글을 DB에서 제거

    Args:
        source: DataSource 객체
        current_urls: 현재 크롤링에서 수집된 URL들의 집합

    Returns:
        삭제된 게시글 수
    """
    if not current_urls:
        # 크롤링 결과가 비어있으면 삭제하지 않음 (크롤링 실패 방지)
        return 0

    # 최소 수집 개수 확인 (너무 적으면 크롤링 실패로 간주)
    min_items = 3
    if len(current_urls) < min_items:
        return 0

    # 해당 소스의 기존 데이터 중 현재 URL에 없는 것들 찾기
    existing_data = CollectedData.objects.filter(source=source)

    deleted_count = 0
    for data in existing_data:
        url = data.data.get('url', '')
        if url and url not in current_urls:
            data.delete()
            deleted_count += 1
            print(f"Deleted old post: {data.data.get('title', '')[:30]}")

    return deleted_count
