from django.core.management.base import BaseCommand
import requests


class Command(BaseCommand):
    help = 'API 엔드포인트 찾기'

    def handle(self, *args, **options):
        # 메이플스토리 공지사항 API 시도
        api_urls = [
            'https://maplestory.nexon.com/News/Notice/List',
            'https://maplestory.nexon.com/api/Notice',
            'https://api.maplestory.nexon.com/notice',
            'https://maplestory.nexon.com/News/Notice?page=1',
        ]

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://maplestory.nexon.com/News/Notice'
        }

        for url in api_urls:
            try:
                self.stdout.write(f"\n시도: {url}")
                response = requests.get(url, headers=headers, timeout=10)

                self.stdout.write(f"상태 코드: {response.status_code}")
                self.stdout.write(f"Content-Type: {response.headers.get('Content-Type')}")

                if response.status_code == 200:
                    content = response.text[:500]
                    self.stdout.write(f"내용 샘플:\n{content}\n")

            except Exception as e:
                self.stdout.write(f"오류: {str(e)}")
