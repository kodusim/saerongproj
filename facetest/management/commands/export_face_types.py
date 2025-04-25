import os
import json
from django.core.management.base import BaseCommand
from facetest.models import FaceModel, FaceType

class Command(BaseCommand):
    help = '얼굴 유형 정보를 JSON 파일로 내보냅니다. 기존 모델의 JSON 파일을 수정하는데 유용합니다.'
    
    def add_arguments(self, parser):
        parser.add_argument('--model-id', type=int, help='모델 ID (지정하지 않으면 활성화된 모델 사용)')
        parser.add_argument('--output', type=str, default='face_types.json', help='출력 파일 경로')
    
    def handle(self, *args, **options):
        model_id = options['model_id']
        output_path = options['output']
        
        # 모델 선택
        if model_id:
            try:
                model = FaceModel.objects.get(id=model_id)
            except FaceModel.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'ID가 {model_id}인 모델을 찾을 수 없습니다.'))
                return
        else:
            model = FaceModel.objects.filter(is_active=True).first()
            if not model:
                self.stderr.write(self.style.ERROR('활성화된 모델이 없습니다.'))
                return
        
        # 얼굴 유형 정보 수집
        face_types = {}
        for face_type in FaceType.objects.filter(model=model):
            # 특징 목록 변환
            characteristics = face_type.get_characteristics_list()
            examples = face_type.get_examples_list()
            
            face_types[face_type.code] = {
                'name': face_type.name,
                'description': face_type.description,
                'characteristics': characteristics,
                'examples': examples
            }
        
        # JSON 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(face_types, f, ensure_ascii=False, indent=2)
        
        self.stdout.write(self.style.SUCCESS(
            f'"{model.name}" 모델의 얼굴 유형 정보가 {output_path}에 저장되었습니다. '
            f'총 {len(face_types)}개의 유형이 내보내졌습니다.'
        ))