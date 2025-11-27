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
        # Chrome 옵션 설정 (메모리 최적화)
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 백그라운드 실행
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--window-size=1280,720')  # 창 크기 축소
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        # 메모리 사용량 최적화 옵션
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--metrics-recording-only')
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--disable-renderer-backgrounding')

        # Linux 서버에서만 google-chrome 경로 지정
        if platform.system() == 'Linux':
            chrome_options.binary_location = '/usr/bin/google-chrome'

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
            "container": ".news_board ul li",  # 목록 아이템 컨테이너 (필수)
            "title": "p a span",               # 제목 선택자 (필수)
            "url": "p a",                      # URL 선택자 (선택, 비우면 container의 href 사용)
            "date": ".heart_date dd",          # 날짜 선택자 (선택)
            "date_attr": "datetime"            # 날짜 속성 (선택, 지정 시 해당 속성값 사용)
        },
        "base_url": "https://maplestory.nexon.com",  # 상대 URL을 절대 URL로 변환할 base
        "wait_selector": ".news_board",      # 로딩 대기할 선택자 (선택사항)
        "game_name": "메이플스토리",         # 게임명 (선택사항)
        "max_items": 20                      # 수집할 최대 개수 (기본: 20)
    }
    """

    def fetch(self) -> str:
        """Selenium으로 페이지 가져오기"""
        # Chrome 옵션 설정 (메모리 최적화)
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--window-size=1280,720')  # 창 크기 축소
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        # 메모리 사용량 최적화 옵션
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--metrics-recording-only')
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--disable-renderer-backgrounding')

        # Linux 서버에서만 google-chrome 경로 지정
        if platform.system() == 'Linux':
            chrome_options.binary_location = '/usr/bin/google-chrome'

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

        container_selector = selectors['container']
        title_selector = selectors['title']
        url_selector = selectors.get('url', '')  # 선택사항 (container가 a 태그면 생략 가능)
        date_selector = selectors.get('date', '')
        date_attr = selectors.get('date_attr', '')  # time 태그의 datetime 속성 등

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
                # url_selector가 비어있으면 container 자체에서 href 추출
                if url_selector:
                    url_elem = item.select_one(url_selector)
                    url = url_elem.get('href', '') if url_elem else ''
                else:
                    # container 자체가 a 태그인 경우
                    url = item.get('href', '')

                if not url:
                    continue

                if url and base_url and not url.startswith('http'):
                    url = base_url + url if url.startswith('/') else base_url + '/' + url

                # 날짜 추출 (선택사항)
                date = ''
                if date_selector:
                    date_elem = item.select_one(date_selector)
                    if date_elem:
                        # date_attr가 지정되면 해당 속성값 사용 (예: datetime)
                        if date_attr:
                            date = date_elem.get(date_attr, '')
                        else:
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

    config 예시:
    {
        "base_url": "https://example.com",
        "game_name": "게임이름",
        "selectors": {
            "container": "a[href*='/news/']",  # 각 게시글 아이템 (필수)
            "title": "div.title",               # 제목 요소 (필수)
            "url": "a.link",                    # URL 요소 (선택, 비우면 container의 href 사용)
            "date": "time",                     # 날짜 요소 (선택)
            "date_attr": "datetime"             # 날짜 속성 (선택, 지정 시 해당 속성값 사용)
        },
        "max_items": 20
    }
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

        container_selector = selectors['container']
        title_selector = selectors['title']
        url_selector = selectors.get('url', '')  # 선택사항 (container가 a 태그면 생략 가능)
        date_selector = selectors.get('date', '')
        date_attr = selectors.get('date_attr', '')  # time 태그의 datetime 속성 등

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
                # url_selector가 비어있으면 container 자체에서 href 추출
                if url_selector:
                    url_elem = item.select_one(url_selector)
                    url = url_elem.get('href', '') if url_elem else ''
                else:
                    # container 자체가 a 태그인 경우
                    url = item.get('href', '')

                if not url:
                    continue

                if url and base_url and not url.startswith('http'):
                    url = base_url + url if url.startswith('/') else base_url + '/' + url

                # 날짜 추출 (선택사항)
                date = ''
                if date_selector:
                    date_elem = item.select_one(date_selector)
                    if date_elem:
                        # date_attr가 지정되면 해당 속성값 사용 (예: datetime)
                        if date_attr:
                            date = date_elem.get(date_attr, '')
                        else:
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


class NaverGameCrawler(BaseCrawler):
    """
    네이버 게임 라운지 크롤러

    네이버 게임 라운지의 게시판을 크롤링합니다.
    JavaScript 렌더링이 필요하므로 Selenium을 사용합니다.

    config 예시:
    {
        "base_url": "https://game.naver.com",
        "game_name": "세븐나이츠 리버스",
        "exclude_pinned": true,  # 고정글 제외 여부 (기본: true)
        "max_items": 20
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
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # 메모리 최적화
        chrome_options.add_argument('--disable-background-networking')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-sync')
        chrome_options.add_argument('--metrics-recording-only')
        chrome_options.add_argument('--mute-audio')

        if platform.system() == 'Linux':
            chrome_options.binary_location = '/usr/bin/google-chrome'

        try:
            driver = webdriver.Chrome(options=chrome_options)
        except:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

        try:
            driver.get(self.data_source.url)
            time.sleep(10)  # 네이버 게임은 로딩이 느림

            # 스크롤하여 추가 컨텐츠 로드
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)

            html = driver.page_source
            return html

        finally:
            driver.quit()

    def parse(self, html: str) -> List[Dict[str, Any]]:
        """HTML 파싱하여 게시글 추출"""
        soup = BeautifulSoup(html, 'lxml')
        items = []

        config = self.data_source.config or {}
        base_url = config.get('base_url', 'https://game.naver.com')
        game_name = config.get('game_name', '')
        exclude_pinned = config.get('exclude_pinned', True)
        max_items = config.get('max_items', 20)

        # 게시글 행 선택
        if exclude_pinned:
            # 고정글 제외: post_board_detail 클래스만 선택 (post_board_fix 제외)
            rows = soup.select('tr[class*="post_board_detail"]')
        else:
            # 모든 글 (고정글 포함)
            rows = soup.select('tr[class*="post_board_detail"], tr[class*="post_board_fix"]')

        for row in rows[:max_items]:
            try:
                # 제목 링크 찾기
                title_link = row.select_one('a[href*="detail"]')
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                if not title or len(title) < 3:
                    continue

                # URL 추출
                href = title_link.get('href', '')
                if href and not href.startswith('http'):
                    url = base_url + href
                else:
                    url = href

                # 날짜 추출 (3번째 td, post_align_center 클래스)
                date_td = row.select_one('td[class*="post_align_center"]')
                date = ''
                if date_td:
                    date_text = date_td.get_text(strip=True)
                    # "11.25" 형식을 "2025-11-25"로 변환
                    if '.' in date_text and len(date_text) <= 5:
                        parts = date_text.split('.')
                        if len(parts) == 2:
                            month, day = parts
                            from datetime import date as dt_date
                            year = dt_date.today().year
                            date = f"{year}-{int(month):02d}-{int(day):02d}"
                    elif '시간' in date_text or '분' in date_text:
                        # "3시간 전" 등은 오늘 날짜로
                        from datetime import date as dt_date
                        date = dt_date.today().isoformat()
                    else:
                        date = date_text

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
