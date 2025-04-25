from django.db import models
import uuid
import os

def file_upload_path(instance, filename):
    """파일 업로드 경로"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('facetest/files', filename)

class FaceTestModel(models.Model):
    """얼굴상 테스트 통합 모델"""
    name = models.CharField("테스트 이름", max_length=100)
    description = models.TextField("설명", blank=True)
    
    # 모델 파일들
    model_file = models.FileField("모델 파일(.pth)", upload_to=file_upload_path)
    result_types_file = models.FileField("결과 유형 파일(JSON)", upload_to=file_upload_path)
    train_script = models.FileField("학습 스크립트(train.py)", upload_to=file_upload_path, blank=True, null=True)
    predict_script = models.FileField("예측 스크립트(predict.py)", upload_to=file_upload_path, blank=True, null=True)
    
    # 기타 설정
    is_active = models.BooleanField("활성화", default=True)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)
    
    class Meta:
        verbose_name = "얼굴상 테스트"
        verbose_name_plural = "얼굴상 테스트"
    
    def __str__(self):
        return self.name