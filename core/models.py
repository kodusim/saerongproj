from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """데이터 대분류 (예: 게임, 농산물, 날씨, 교통, 아이돌)"""
    name = models.CharField(max_length=100, unique=True, verbose_name="카테고리명")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="슬러그")
    description = models.TextField(blank=True, verbose_name="설명")
    icon = models.CharField(max_length=50, blank=True, verbose_name="아이콘",
                           help_text="이모지 또는 아이콘 클래스명")
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    order = models.IntegerField(default=0, verbose_name="정렬 순서")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "카테고리"
        verbose_name_plural = "카테고리 목록"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class SubCategory(models.Model):
    """데이터 중분류 (예: 게임 -> 공지사항, 이벤트, 뉴스)"""
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name="상위 카테고리"
    )
    name = models.CharField(max_length=100, verbose_name="하위 카테고리명")
    slug = models.SlugField(max_length=100, verbose_name="슬러그")
    description = models.TextField(blank=True, verbose_name="설명")
    is_active = models.BooleanField(default=True, verbose_name="활성화")
    order = models.IntegerField(default=0, verbose_name="정렬 순서")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")

    class Meta:
        verbose_name = "하위 카테고리"
        verbose_name_plural = "하위 카테고리 목록"
        ordering = ['order', 'name']
        unique_together = [['category', 'slug']]

    def __str__(self):
        return f"{self.category.name} > {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)
