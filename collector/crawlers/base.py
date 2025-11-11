import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime
import requests
from bs4 import BeautifulSoup


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

            # 3. 유효성 검사 및 해시 생성
            valid_items = []
            for item in items:
                if self.validate(item):
                    item['hash_key'] = self.generate_hash(item)
                    valid_items.append(item)

            return valid_items

        except Exception as e:
            raise Exception(f"Crawling failed: {str(e)}")
