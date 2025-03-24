from django.db import models
from django.urls import reverse


class Test(models.Model):
    """심리 테스트 모델"""
    title = models.CharField("제목", max_length=100)
    description = models.TextField("설명")
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    
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
    
    def __str__(self):
        return self.text


class Result(models.Model):
    """테스트 결과 모델"""
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='results', verbose_name="테스트")
    title = models.CharField("결과 제목", max_length=100)
    description = models.TextField("결과 설명")
    min_score = models.IntegerField("최소 점수")
    max_score = models.IntegerField("최대 점수")
    
    def __str__(self):
        return f"{self.test.title} - {self.title}"