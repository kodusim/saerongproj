import hashlib
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime, date
import requests
from bs4 import BeautifulSoup


def normalize_date(date_str: str) -> str:
    """
    다양한 날짜 형식을 YYYY-MM-DD로 정규화

    지원 형식:
    - "2025.11.25" → "2025-11-25"
    - "2025-11-25" → "2025-11-25" (이미 정규화됨)
    - "PM 02:39", "AM 10:00" → 오늘 날짜 "2025-11-26"
    - "2025.11.20 ~ 2025.12.18" → 시작일 "2025-11-20"
    - "11/25" → 올해 날짜 "2025-11-25"
    - 파싱 실패 시 → 오늘 날짜
    """
    if not date_str:
        return date.today().isoformat()

    date_str = date_str.strip()
    today = date.today()

    # 1. 이미 정규화된 형식 (YYYY-MM-DD)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str

    # 2. YYYY.MM.DD 형식
    match = re.match(r'^(\d{4})\.(\d{1,2})\.(\d{1,2})', date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # 3. MM/DD 형식 (올해로 가정)
    match = re.match(r'^(\d{1,2})/(\d{1,2})$', date_str)
    if match:
        month, day = match.groups()
        return f"{today.year}-{int(month):02d}-{int(day):02d}"

    # 4. 시간만 있는 경우 (AM/PM HH:MM) → 오늘 날짜
    if re.match(r'^(AM|PM)\s*\d{1,2}:\d{2}', date_str, re.IGNORECASE):
        return today.isoformat()

    # 5. 시간만 있는 경우 (HH:MM) → 오늘 날짜
    if re.match(r'^\d{1,2}:\d{2}$', date_str):
        return today.isoformat()

    # 6. 파싱 실패 시 오늘 날짜 반환
    return today.isoformat()


class BaseCrawler(ABC):
    """크롤러 기본 클래스"""

    def __init__(self, data_source):
        """
        Args:
            data_source: DataSource 모델 인스턴스
        """
        self.data_source = data_source
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    @abstractmethod
    def fetch(self) -> str:
        """데이터를 가져오는 메서드 (오버라이드 필수)"""
        pass

    @abstractmethod
    def parse(self, html: str) -> List[Dict[str, Any]]:
        """HTML을 파싱하여 데이터를 추출 (오버라이드 필수)"""
        pass

    def generate_hash(self, data: Dict[str, Any]) -> str:
        """데이터의 고유 해시값 생성"""
        # 제목 + URL로 해시 생성
        unique_str = f"{data.get('title', '')}{data.get('url', '')}"
        return hashlib.sha256(unique_str.encode()).hexdigest()

    def validate(self, data: Dict[str, Any]) -> bool:
        """데이터 유효성 검사"""
        required_fields = ['title', 'url']
        return all(field in data for field in required_fields)

    def crawl(self) -> List[Dict[str, Any]]:
        """전체 크롤링 프로세스 실행"""
        try:
            # 1. 데이터 가져오기
            html = self.fetch()

            # 2. 파싱
            items = self.parse(html)

            # 3. 유효성 검사, 날짜 정규화 및 해시 생성
            valid_items = []
            for item in items:
                if self.validate(item):
                    # 날짜 정규화 (YYYY-MM-DD 형식으로 통일)
                    if 'date' in item:
                        item['date'] = normalize_date(item['date'])
                    item['hash_key'] = self.generate_hash(item)
                    valid_items.append(item)

            return valid_items

        except Exception as e:
            raise Exception(f"Crawling failed: {str(e)}")
