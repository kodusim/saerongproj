from django.db import models
from django.urls import reverse
import uuid
import os

def face_image_upload_path(instance, filename):
    """업로드된 얼굴 이미지의 저장 경로"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('face_images', filename)

def model_file_upload_path(instance, filename):
    """모델 파일 업로드 경로"""
    return os.path.join('face_models', filename)

def face_type_image_upload_path(instance, filename):
    """얼굴 유형 이미지 업로드 경로"""
    ext = filename.split('.')[-1]
    return os.path.join('face_types', f"{instance.code}_{uuid.uuid4()}.{ext}")

class FaceModel(models.Model):
    """얼굴상 테스트 모델"""
    name = models.CharField("모델명", max_length=100)
    description = models.TextField("설명", blank=True)
    model_file = models.FileField("모델 파일", upload_to=model_file_upload_path)
    face_types_json = models.JSONField("얼굴 유형 데이터", default=dict, blank=True)
    is_active = models.BooleanField("활성화", default=True)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    
    class Meta:
        verbose_name = "얼굴상 모델"
        verbose_name_plural = "얼굴상 모델"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class FaceType(models.Model):
    """얼굴 유형 모델"""
    name = models.CharField("유형명", max_length=50)
    code = models.CharField("코드", max_length=50, help_text="모델이 예측에 사용하는 클래스명")
    description = models.TextField("설명")
    characteristics = models.TextField("특징", help_text="특징을 한 줄에 하나씩 작성하세요", blank=True)
    examples = models.TextField("예시", help_text="예시를 한 줄에 하나씩 작성하세요", blank=True)
    image = models.ImageField("대표 이미지", upload_to=face_type_image_upload_path, blank=True)
    model = models.ForeignKey(FaceModel, on_delete=models.CASCADE, related_name="face_types", verbose_name="모델")
    
    class Meta:
        verbose_name = "얼굴 유형"
        verbose_name_plural = "얼굴 유형"
        unique_together = [('code', 'model')]
    
    def __str__(self):
        return f"{self.name} ({self.model.name})"
    
    def get_characteristics_list(self):
        """특징을 리스트로 반환"""
        if not self.characteristics:
            return []
        return [line.strip() for line in self.characteristics.split('\n') if line.strip()]
    
    def get_examples_list(self):
        """예시를 리스트로 반환"""
        if not self.examples:
            return []
        return [line.strip() for line in self.examples.split('\n') if line.strip()]

class FaceTestResult(models.Model):
    """얼굴 테스트 결과 모델"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField("얼굴 이미지", upload_to=face_image_upload_path)
    face_type = models.ForeignKey(FaceType, on_delete=models.CASCADE, related_name="results", verbose_name="얼굴 유형")
    probability = models.FloatField("확률")
    all_results = models.JSONField("모든 결과", default=dict)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "얼굴 테스트 결과"
        verbose_name_plural = "얼굴 테스트 결과"
    
    def __str__(self):
        return f"{self.face_type.name} ({self.probability:.1%})"
    
    def get_absolute_url(self):
        return reverse('facetest:result_detail', args=[str(self.id)])