from django.core.management.base import BaseCommand
from sources.models import DataSource
import requests
from bs4 import BeautifulSoup


class Command(BaseCommand):
    help = 'HTML 구조를 분석하여 올바른 셀렉터 찾기'

    def add_arguments(self, parser):
        parser.add_argument('source_id', type=int, help='데이터 소스 ID')

    def handle(self, *args, **options):
        source_id = options['source_id']

        try:
            source = DataSource.objects.get(id=source_id)
            self.stdout.write(f"데이터 소스: {source.name}")
            self.stdout.write(f"URL: {source.url}\n")

            # HTML 가져오기
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            response = session.get(source.url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')

            # 다양한 셀렉터 시도
            selectors = [
                '.notice_list li',
                '.board-list tr',
                'table tr',
                'ul li',
                '.news_list li',
                '.list li',
                'article',
                '.item',
                '[class*="notice"]',
                '[class*="list"]',
            ]

            self.stdout.write(self.style.SUCCESS("\n[가능한 셀렉터 분석]"))

            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    self.stdout.write(f"\n[OK] '{selector}': {len(elements)}개 발견")

                    # 첫 번째 요소 샘플 출력
                    if len(elements) > 0:
                        first = elements[0]
                        self.stdout.write(f"  샘플: {str(first)[:200]}...")

            # 링크가 있는 요소 찾기
            self.stdout.write(self.style.SUCCESS("\n\n[링크 분석]"))
            links = soup.select('a')
            self.stdout.write(f"총 {len(links)}개의 링크 발견")

            # 공지사항 같은 링크 찾기
            notice_keywords = ['공지', 'notice', '뉴스', 'news', '업데이트', 'update']
            relevant_links = []

            for link in links[:30]:  # 처음 30개만
                text = link.get_text(strip=True)
                href = link.get('href', '')

                if any(keyword in text.lower() or keyword in href.lower() for keyword in notice_keywords):
                    relevant_links.append((text, href))

            if relevant_links:
                self.stdout.write("\n관련 링크 샘플:")
                for text, href in relevant_links[:5]:
                    self.stdout.write(f"  제목: {text}")
                    self.stdout.write(f"  URL: {href}\n")

        except DataSource.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"데이터 소스를 찾을 수 없습니다: ID {source_id}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"오류: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
