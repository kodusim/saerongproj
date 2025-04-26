from django.db import models
import uuid
import os
import json
from django.core.exceptions import ValidationError

def file_upload_path(instance, filename):
    """파일 업로드 경로"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('facetest/files', filename)

def result_image_upload_path(instance, filename):
    """결과 이미지 업로드 경로"""
    ext = filename.split('.')[-1]
    
    # Check if the instance is a FaceResultType or has a result_type attribute
    if hasattr(instance, 'result_type'):
        # This is a FaceResultImage instance
        result_type = instance.result_type
    else:
        # This is a FaceResultType instance itself
        result_type = instance
    
    safe_name = result_type.name.replace(' ', '_')
    filename = f"{safe_name}_{uuid.uuid4()}.{ext}"
    return os.path.join('facetest/result_images', filename)

def test_image_upload_path(instance, filename):
    """테스트 대표 이미지 업로드 경로"""
    ext = filename.split('.')[-1]
    safe_name = instance.name.replace(' ', '_')
    filename = f"{safe_name}_{uuid.uuid4()}.{ext}"
    return os.path.join('facetest/test_images', filename)

class FaceTestModel(models.Model):
    """얼굴상 테스트 통합 모델"""
    name = models.CharField("테스트 이름", max_length=100)
    description = models.TextField("설명", blank=True)
    view_count = models.PositiveIntegerField("조회수", default=0)
    
    # 이미지 필드들
    image = models.ImageField("대표 이미지", upload_to=test_image_upload_path, null=True, blank=True, 
                             help_text="권장 크기: 140x160px, 테스트 목록에 표시됩니다.")
    intro_image = models.ImageField("인트로 이미지", upload_to=test_image_upload_path, null=True, blank=True,
                                  help_text="권장 크기: 500x500px, 테스트 시작 페이지에 표시됩니다.")
    guide_image = models.ImageField("업로드 가이드 이미지", upload_to=test_image_upload_path, null=True, blank=True,
                                  help_text="권장 크기: 500x300px, 얼굴 업로드 가이드로 표시됩니다.")
    
    # 모델 파일들
    model_file = models.FileField("모델 파일(.pth)", upload_to=file_upload_path)
    result_types_file = models.FileField("결과 유형 파일(JSON)", upload_to=file_upload_path)
    train_script = models.FileField("학습 스크립트(train.py)", upload_to=file_upload_path, blank=True, null=True)
    predict_script = models.FileField("예측 스크립트(predict.py)", upload_to=file_upload_path, blank=True, null=True)
    
    # 추가 텍스트 필드
    upload_guide = models.TextField("업로드 가이드", blank=True, 
                                   help_text="얼굴 이미지 업로드시 표시할 가이드 텍스트입니다.")
    
    # 기타 설정
    is_active = models.BooleanField("활성화", default=True)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)
    
    class Meta:
        verbose_name = "얼굴상 테스트"
        verbose_name_plural = "얼굴상 테스트"
    
    def __str__(self):
        return self.name
    
    def increase_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])
        
    def save(self, *args, **kwargs):
        """저장 시 JSON 파일이 있으면 결과 유형 자동 생성"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # 신규 모델이거나 result_types_file이 변경되었을 때만 실행
        if is_new or 'result_types_file' in kwargs.get('update_fields', []):
            self.sync_result_types()
    
    def sync_result_types(self):
        """JSON 파일에서 결과 유형을 읽어와 동기화"""
        if not self.result_types_file:
            return
            
        try:
            json_content = self.result_types_file.read().decode('utf-8')
            result_types_data = json.loads(json_content)
            
            # 기존 결과 유형 ID 목록
            existing_type_ids = set(self.result_types.values_list('type_id', flat=True))
            processed_type_ids = set()
            
            # JSON의 각 결과 유형에 대해 처리
            for type_name, type_data in result_types_data.items():
                type_id = type_data.get('id')
                if type_id is None:
                    continue
                    
                processed_type_ids.add(type_id)
                
                # 설명과 특성, 예시 추출
                description = type_data.get('description', '')
                characteristics = type_data.get('characteristics', [])
                examples = type_data.get('examples', [])
                
                # 특성과 예시를 JSON 문자열로 변환
                characteristics_json = json.dumps(characteristics, ensure_ascii=False)
                examples_json = json.dumps(examples, ensure_ascii=False)
                
                # 결과 유형 생성 또는 업데이트
                result_type, created = FaceResultType.objects.update_or_create(
                    face_test=self,
                    type_id=type_id,
                    defaults={
                        'name': type_name,
                        'description': description,
                        'characteristics': characteristics_json,
                        'examples': examples_json
                    }
                )
            
            # 더 이상 존재하지 않는 결과 유형 삭제
            obsolete_type_ids = existing_type_ids - processed_type_ids
            if obsolete_type_ids:
                FaceResultType.objects.filter(face_test=self, type_id__in=obsolete_type_ids).delete()
                
        except Exception as e:
            # 오류 발생 시 저장하지 않고 오류 메시지 표시
            raise ValidationError(f"결과 유형 파일 처리 중 오류 발생: {str(e)}")


class FaceResultType(models.Model):
    """얼굴상 테스트 결과 유형"""
    face_test = models.ForeignKey(FaceTestModel, on_delete=models.CASCADE, related_name='result_types', verbose_name="테스트")
    type_id = models.IntegerField("유형 ID")
    name = models.CharField("유형 이름", max_length=100)
    description = models.TextField("설명")
    characteristics = models.TextField("특성(JSON)", help_text="특성 목록을 JSON 형식으로 저장")
    examples = models.TextField("예시(JSON)", help_text="예시 목록을 JSON 형식으로 저장", blank=True)
    background_color = models.CharField("배경색", max_length=20, default="#FFF5EE", 
                             help_text="예: #FFFFFF, rgb(255,255,255), mintcream 등")
    sub_image = models.ImageField("결과 보조 이미지", upload_to=result_image_upload_path, null=True, blank=True,
                            help_text="권장 크기: 500x300px, 결과 설명 대신 표시됩니다.")
    
    class Meta:
        verbose_name = "얼굴상 결과 유형"
        verbose_name_plural = "얼굴상 결과 유형"
        unique_together = [('face_test', 'type_id')]
        ordering = ['face_test', 'type_id']
    
    def __str__(self):
        return f"{self.face_test.name} - {self.name}"
    
    def get_characteristics_list(self):
        """특성 목록 반환"""
        try:
            return json.loads(self.characteristics)
        except:
            return []
    
    def get_examples_list(self):
        """예시 목록 반환"""
        try:
            return json.loads(self.examples)
        except:
            return []


class FaceResultImage(models.Model):
    """얼굴상 결과 유형별 이미지"""
    result_type = models.ForeignKey(FaceResultType, on_delete=models.CASCADE, related_name='images', verbose_name="결과 유형")
    image = models.ImageField("이미지", upload_to=result_image_upload_path)
    title = models.CharField("제목", max_length=100, blank=True)
    order = models.PositiveIntegerField("순서", default=0)
    is_main = models.BooleanField("대표 이미지", default=False)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    
    class Meta:
        verbose_name = "얼굴상 결과 이미지"
        verbose_name_plural = "얼굴상 결과 이미지"
        ordering = ['result_type', 'order', 'id']
    
    def __str__(self):
        img_title = self.title if self.title else f"이미지 {self.id}"
        return f"{self.result_type.name} - {img_title}"
    
    def save(self, *args, **kwargs):
        """저장 시 대표 이미지가 변경되면 다른 이미지를 업데이트"""
        if self.is_main and not self._state.adding:
            # 기존 대표 이미지들을 일반 이미지로 변경
            FaceResultImage.objects.filter(
                result_type=self.result_type, 
                is_main=True
            ).exclude(pk=self.pk).update(is_main=False)
            
        super().save(*args, **kwargs)