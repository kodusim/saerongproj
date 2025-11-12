from django.db import models
from django.utils.text import slugify
from core.models import SubCategory
import re


class DataSource(models.Model):
    """크롤링 대상 데이터 소스 (예: 롤 공지사항, 로아 이벤트)"""

    CRAWLER_TYPE_CHOICES = [
        ('beautifulsoup', 'BeautifulSoup'),
        ('selenium', 'Selenium'),
        ('api', 'API'),
        ('rss', 'RSS'),
    ]

    subcategory = models.ForeignKey(
        SubCategory,
        on_delete=models.CASCADE,
        related_name='data_sources',
        verbose_name="하위 카테고리"
    )
    name = models.CharField(max_length=200, verbose_name="데이터 소스명",
                           help_text="예: 리그오브레전드 공지사항")
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name="슬러그",
                           help_text="비워두면 자동으로 생성됩니다")
    url = models.URLField(max_length=500, verbose_name="크롤링 URL")
    crawler_type = models.CharField(
        max_length=20,
        choices=CRAWLER_TYPE_CHOICES,
        default='beautifulsoup',
        verbose_name="크롤러 타입"
    )
    crawler_class = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="크롤러 클래스명",
        help_text="예: collector.crawlers.game_crawlers.LOLNoticeCrawler"
    )
    crawl_interval = models.IntegerField(
        default=10,
        verbose_name="크롤링 주기(분)",
        help_text="몇 분마다 크롤링할지 설정"
    )
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    last_crawled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="마지막 크롤링 시간"
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="크롤러 설정",
        help_text="크롤러별 추가 설정을 JSON 형식으로 저장"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "데이터 소스"
        verbose_name_plural = "데이터 소스 목록"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subcategory} - {self.name}"

    def save(self, *args, **kwargs):
        """slug가 비어있으면 name에서 자동 생성"""
        if not self.slug:
            # 한글 및 영문 유지, 특수문자는 하이픈으로 변경
            base_slug = re.sub(r'[^\w\s-]', '', self.name)
            base_slug = re.sub(r'[\s_]+', '-', base_slug)
            base_slug = base_slug.strip('-').lower()

            # slug가 비어있으면 ID 기반으로 생성
            if not base_slug:
                base_slug = f'datasource-{self.id or ""}'

            # 중복 방지를 위해 고유한 slug 생성
            slug = base_slug
            counter = 1
            while DataSource.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)
