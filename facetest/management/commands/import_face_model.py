import os
import json
import shutil
from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from facetest.models import FaceModel, FaceType

class Command(BaseCommand):
    help = '얼굴상 테스트 모델과 얼굴 유형 정보를 가져옵니다.'
    
    def add_arguments(self, parser):
        parser.add_argument('--model-file', type=str, required=True, help='학습된 모델 파일 경로 (.pth)')
        parser.add_argument('--types-file', type=str, required=True, help='얼굴 유형 정보 파일 경로 (.json)')
        parser.add_argument('--name', type=str, default='기본 얼굴상 모델', help='모델 이름')
        parser.add_argument('--description', type=str, default='얼굴상 테스트 기본 모델', help='모델 설명')
        parser.add_argument('--active', action='store_true', help='활성화 여부')
        parser.add_argument('--images-dir', type=str, help='얼굴 유형 이미지가 있는 디렉토리 (선택사항)')
    
    def handle(self, *args, **options):
        model_file_path = options['model_file']
        types_file_path = options['types_file']
        model_name = options['name']
        model_description = options['description']
        is_active = options['active']
        images_dir = options.get('images_dir')
        
        # 파일 존재 확인
        if not os.path.exists(model_file_path):
            self.stderr.write(self.style.ERROR(f'모델 파일을 찾을 수 없습니다: {model_file_path}'))
            return
        
        if not os.path.exists(types_file_path):
            self.stderr.write(self.style.ERROR(f'얼굴 유형 정보 파일을 찾을 수 없습니다: {types_file_path}'))
            return
        
        try:
            # 1. 모델 생성
            with open(model_file_path, 'rb') as f:
                face_model = FaceModel(
                    name=model_name,
                    description=model_description,
                    is_active=is_active
                )
                face_model.model_file.save(os.path.basename(model_file_path), File(f), save=True)
            
            # 유형 정보 파일도 저장
            with open(types_file_path, 'rb') as f:
                face_model.types_json.save(os.path.basename(types_file_path), File(f), save=True)
            
            self.stdout.write(self.style.SUCCESS(f'모델이 생성되었습니다: {face_model.name}'))
            
            # 2. 얼굴 유형 정보 로드
            with open(types_file_path, 'r', encoding='utf-8') as f:
                face_types_data = json.load(f)
            
            # 3. 얼굴 유형 생성
            for type_code, type_info in face_types_data.items():
                # type_info에 name이 없으면 type_code를 name으로 사용
                face_type_name = type_info.get('name', type_code)
                
                face_type = FaceType(
                    model=face_model,
                    name=face_type_name,
                    code=type_code,
                    description=type_info.get('description', f'{type_code} 유형입니다.')
                )
                
                # 특징과 예시 처리
                characteristics = type_info.get('characteristics', [])
                examples = type_info.get('examples', [])
                
                face_type.characteristics = '\n'.join(characteristics)
                face_type.examples = '\n'.join(examples)
                
                # 저장
                face_type.save()
                
                # 이미지가 있으면 이미지도 저장
                if images_dir and os.path.exists(images_dir):
                    # 확장자 찾기
                    image_patterns = [
                        f"{type_code}.jpg", 
                        f"{type_code}.png", 
                        f"{type_code}.jpeg", 
                        f"{face_type_name}.jpg", 
                        f"{face_type_name}.png", 
                        f"{face_type_name}.jpeg"
                    ]
                    
                    for pattern in image_patterns:
                        image_path = os.path.join(images_dir, pattern)
                        if os.path.exists(image_path):
                            with open(image_path, 'rb') as img_file:
                                face_type.image.save(
                                    os.path.basename(image_path), 
                                    File(img_file), 
                                    save=True
                                )
                            self.stdout.write(f"  - {face_type.name}의 이미지를 저장했습니다: {pattern}")
                            break
                
                self.stdout.write(f'  - 얼굴 유형 생성: {face_type.name} ({face_type.code})')
            
            self.stdout.write(self.style.SUCCESS(f'총 {len(face_types_data)} 개의 얼굴 유형이 생성되었습니다.'))
            
            # 기존 활성화 모델 비활성화 (현재 모델을 활성화하는 경우)
            if is_active:
                FaceModel.objects.exclude(id=face_model.id).update(is_active=False)
                self.stdout.write(self.style.SUCCESS(f'"{face_model.name}" 모델이 활성화되었습니다.'))
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'가져오기 오류: {str(e)}'))
            import traceback
            self.stderr.write(traceback.format_exc())