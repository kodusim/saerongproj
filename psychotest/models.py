from django.db import models
from django.urls import reverse


class Category(models.Model):
    """테스트 카테고리 모델"""
    name = models.CharField("카테고리명", max_length=50)
    description = models.TextField("설명", blank=True)
    
    class Meta:
        verbose_name = "카테고리"
        verbose_name_plural = "카테고리들"
    
    def __str__(self):
        return self.name


class Test(models.Model):
    """심리 테스트 모델"""
    title = models.CharField("제목", max_length=100)
    description = models.TextField("설명")
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name="tests", verbose_name="카테고리")
    calculation_method = models.CharField("결과 계산 방식", max_length=20, choices=[
        ('sum', '점수 합산'),
        ('category', '카테고리 점수'),
        ('pattern', '패턴 매칭'),
    ], default='sum')
    view_style = models.CharField("보기 방식", max_length=20, choices=[
        ('all', '모든 질문 한번에'),
        ('one', '한 질문씩'),
    ], default='all')
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('psychotest:test_detail', args=[self.id])


class Question(models.Model):
    """테스트 질문 모델"""
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions', verbose_name="테스트")
    text = models.TextField("질문 내용")
    order = models.PositiveSmallIntegerField("순서", default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.test.title} - {self.text[:30]}"


class Option(models.Model):
    """질문 선택지 모델"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options', verbose_name="질문")
    text = models.CharField("텍스트", max_length=200)
    score = models.IntegerField("점수", default=0)
    category_scores = models.JSONField("카테고리별 점수", blank=True, null=True, 
                                      help_text="{'A': 2, 'B': 1} 형태로 각 카테고리별 점수를 저장")
    
    def __str__(self):
        return self.text


class Result(models.Model):
    """테스트 결과 모델"""
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='results', verbose_name="테스트")
    title = models.CharField("결과 제목", max_length=100)
    description = models.TextField("결과 설명")
    min_score = models.IntegerField("최소 점수", null=True, blank=True)
    max_score = models.IntegerField("최대 점수", null=True, blank=True)
    category = models.CharField("카테고리", max_length=50, blank=True, null=True,
                              help_text="카테고리 계산 방식에서 사용되는 카테고리 값")
    
    def __str__(self):
        return f"{self.test.title} - {self.title}"