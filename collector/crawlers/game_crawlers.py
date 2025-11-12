from typing import List, Dict, Any
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
import platform
from .base import BaseCrawler


class MapleStoryCrawler(BaseCrawler):
    """메이플스토리 공지사항 크롤러 (Selenium 사용)"""

    def fetch(self) -> str:
        """메이플스토리 공지사항 페이지 가져오기 (Selenium)"""
        # Chrome 옵션 설정
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 백그라운드 실행
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.add_argument('--remote-debugging-port=9222')

        # Linux 서버에서만 chromium-browser 경로 지정
        if platform.system() == 'Linux':
            chrome_options.binary_location = '/usr/bin/chromium-browser'

        # 드라이버 초기화
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except:
            # webdriver-manager로 자동 설치
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

        try:
            # 페이지 로드
            driver.get(self.data_source.url)

            # JavaScript 실행 대기 (최대 10초)
            time.sleep(3)  # 초기 로딩 대기

            # 공지사항 목록이 로드될 때까지 대기
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.news_board, table, .board'))
                )
            except:
                pass  # 타임아웃되어도 계속 진행

            # 페이지 스크롤 (동적 로딩이 있을 경우)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            # HTML 가져오기
            html = driver.page_source
            return html

        finally:
            driver.quit()

    def parse(self, html: str) -> List[Dict[str, Any]]:
        """HTML 파싱하여 공지사항 추출"""
        soup = BeautifulSoup(html, 'lxml')
        items = []

        # 메이플스토리 공지사항 구조: .news_board ul li
        notice_items = soup.select('.news_board ul li')

        for item in notice_items[:20]:  # 최근 20개만
            try:
                # 링크 요소 찾기
                link = item.select_one('p a')
                if not link:
                    continue

                # 제목 추출 (span 내의 텍스트)
                title_elem = link.select_one('span')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                if not title or len(title) < 3:  # 너무 짧은 제목 제외
                    continue

                # URL 추출
                url = link.get('href', '')
                if url and not url.startswith('http'):
                    base_url = 'https://maplestory.nexon.com'
                    url = base_url + url if url.startswith('/') else base_url + '/' + url

                # 날짜 추출 (.heart_date dd)
                date_elem = item.select_one('.heart_date dd')
                date = date_elem.get_text(strip=True) if date_elem else ''

                # 카테고리 추출 (이미지의 alt 속성에서)
                category_img = link.select_one('em img')
                category = '일반'
                if category_img:
                    alt_text = category_img.get('alt', '')
                    # [공지], [점검], [업데이트] 등에서 괄호 제거
                    category = alt_text.strip('[]')

                data = {
                    'type': 'game_notice',
                    'game': '메이플스토리',
                    'title': title,
                    'url': url,
                    'date': date,
                    'category': category,
                }

                items.append(data)

            except Exception as e:
                # 개별 아이템 파싱 실패 시 건너뛰기
                continue

        return items


class GenericSeleniumCrawler(BaseCrawler):
    """
    범용 Selenium 크롤러 (JavaScript 렌더링이 필요한 사이트)

    DataSource의 config에서 CSS 선택자를 읽어서 동작

    config 예시:
    {
        "selectors": {
            "container": ".news_board ul li",  # 목록 아이템 컨테이너
            "title": "p a span",               # 제목 선택자
            "url": "p a",                       # URL 링크 선택자
            "date": ".heart_date dd"           # 날짜 선택자 (선택사항)
        },
        "base_url": "https://maplestory.nexon.com",  # 상대 URL을 절대 URL로 변환할 base
        "wait_selector": ".news_board",      # 로딩 대기할 선택자 (선택사항)
        "game_name": "메이플스토리",         # 게임명 (선택사항)
        "max_items": 20                      # 수집할 최대 개수 (기본: 20)
    }
    """

    def fetch(self) -> str:
        """Selenium으로 페이지 가져오기"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.add_argument('--remote-debugging-port=9222')

        # Linux 서버에서만 chromium-browser 경로 지정
        if platform.system() == 'Linux':
            chrome_options.binary_location = '/usr/bin/chromium-browser'

        try:
            driver = webdriver.Chrome(options=chrome_options)
        except:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

        try:
            driver.get(self.data_source.url)
            time.sleep(3)  # 초기 로딩 대기

            # config에서 대기할 선택자 가져오기
            wait_selector = self.data_source.config.get('wait_selector')
            if wait_selector:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                    )
                except:
                    pass

            # 페이지 스크롤
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            html = driver.page_source
            return html

        finally:
            driver.quit()

    def parse(self, html: str) -> List[Dict[str, Any]]:
        """config의 선택자를 사용하여 HTML 파싱"""
        soup = BeautifulSoup(html, 'lxml')
        items = []

        # config에서 선택자 가져오기
        config = self.data_source.config
        selectors = config.get('selectors', {})

        if not selectors.get('container'):
            raise ValueError("config에 'selectors.container'가 필요합니다")
        if not selectors.get('title'):
            raise ValueError("config에 'selectors.title'이 필요합니다")
        if not selectors.get('url'):
            raise ValueError("config에 'selectors.url'이 필요합니다")

        container_selector = selectors['container']
        title_selector = selectors['title']
        url_selector = selectors['url']
        date_selector = selectors.get('date', '')

        base_url = config.get('base_url', '')
        game_name = config.get('game_name', '')
        max_items = config.get('max_items', 20)

        # 컨테이너 아이템들 찾기
        notice_items = soup.select(container_selector)

        for item in notice_items[:max_items]:
            try:
                # 제목 추출
                title_elem = item.select_one(title_selector)
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                if not title or len(title) < 3:
                    continue

                # URL 추출
                url_elem = item.select_one(url_selector)
                if not url_elem:
                    continue

                url = url_elem.get('href', '')
                if url and base_url and not url.startswith('http'):
                    url = base_url + url if url.startswith('/') else base_url + '/' + url

                # 날짜 추출 (선택사항)
                date = ''
                if date_selector:
                    date_elem = item.select_one(date_selector)
                    if date_elem:
                        date = date_elem.get_text(strip=True)

                data = {
                    'type': 'game_notice',
                    'title': title,
                    'url': url,
                    'date': date,
                }

                if game_name:
                    data['game'] = game_name

                items.append(data)

            except Exception as e:
                continue

        return items


class GenericRequestsCrawler(BaseCrawler):
    """
    범용 Requests 크롤러 (정적 HTML 사이트용, 더 빠름)

    JavaScript 렌더링이 필요없는 사이트에 사용
    config 형식은 GenericSeleniumCrawler와 동일
    """

    def fetch(self) -> str:
        """Requests로 페이지 가져오기"""
        response = self.session.get(self.data_source.url, timeout=30)
        response.raise_for_status()
        return response.text

    def parse(self, html: str) -> List[Dict[str, Any]]:
        """config의 선택자를 사용하여 HTML 파싱"""
        soup = BeautifulSoup(html, 'lxml')
        items = []

        # config에서 선택자 가져오기
        config = self.data_source.config
        selectors = config.get('selectors', {})

        if not selectors.get('container'):
            raise ValueError("config에 'selectors.container'가 필요합니다")
        if not selectors.get('title'):
            raise ValueError("config에 'selectors.title'이 필요합니다")
        if not selectors.get('url'):
            raise ValueError("config에 'selectors.url'이 필요합니다")

        container_selector = selectors['container']
        title_selector = selectors['title']
        url_selector = selectors['url']
        date_selector = selectors.get('date', '')

        base_url = config.get('base_url', '')
        game_name = config.get('game_name', '')
        max_items = config.get('max_items', 20)

        # 컨테이너 아이템들 찾기
        notice_items = soup.select(container_selector)

        for item in notice_items[:max_items]:
            try:
                # 제목 추출
                title_elem = item.select_one(title_selector)
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                if not title or len(title) < 3:
                    continue

                # URL 추출
                url_elem = item.select_one(url_selector)
                if not url_elem:
                    continue

                url = url_elem.get('href', '')
                if url and base_url and not url.startswith('http'):
                    url = base_url + url if url.startswith('/') else base_url + '/' + url

                # 날짜 추출 (선택사항)
                date = ''
                if date_selector:
                    date_elem = item.select_one(date_selector)
                    if date_elem:
                        date = date_elem.get_text(strip=True)

                data = {
                    'type': 'game_notice',
                    'title': title,
                    'url': url,
                    'date': date,
                }

                if game_name:
                    data['game'] = game_name

                items.append(data)

            except Exception as e:
                continue

        return items
