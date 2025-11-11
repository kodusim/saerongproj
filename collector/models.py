from django.db import models
from sources.models import DataSource


class CollectedData(models.Model):
    """수집된 데이터 (유연한 JSON 구조)"""

    source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name='collected_data',
        verbose_name="데이터 소스"
    )
    data = models.JSONField(
        verbose_name="수집된 데이터",
        help_text="각 타입마다 다른 구조를 가질 수 있음"
    )
    hash_key = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="해시 키",
        help_text="중복 데이터 방지를 위한 해시값"
    )
    collected_at = models.DateTimeField(auto_now_add=True, verbose_name="수집일시")

    class Meta:
        verbose_name = "수집 데이터"
        verbose_name_plural = "수집 데이터 목록"
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['-collected_at']),
            models.Index(fields=['source', '-collected_at']),
        ]

    def __str__(self):
        return f"{self.source.name} - {self.collected_at.strftime('%Y-%m-%d %H:%M')}"


class CrawlLog(models.Model):
    """크롤링 실행 로그"""

    STATUS_CHOICES = [
        ('success', '성공'),
        ('failed', '실패'),
        ('partial', '부분 성공'),
    ]

    source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name='crawl_logs',
        verbose_name="데이터 소스"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name="상태"
    )
    items_collected = models.IntegerField(default=0, verbose_name="수집 건수")
    error_message = models.TextField(blank=True, verbose_name="에러 메시지")
    started_at = models.DateTimeField(verbose_name="시작 시간")
    completed_at = models.DateTimeField(verbose_name="완료 시간")
    duration_seconds = models.FloatField(verbose_name="소요 시간(초)")

    class Meta:
        verbose_name = "크롤링 로그"
        verbose_name_plural = "크롤링 로그 목록"
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.source.name} - {self.status} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
