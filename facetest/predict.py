import os
import torch
import torchvision.transforms as transforms
import torchvision.models as models
import torch.nn as nn
from PIL import Image
import numpy as np
from django.conf import settings

# 모델 클래스 정의
class FaceModel(nn.Module):
    def __init__(self, num_classes):
        super(FaceModel, self).__init__()
        self.model = models.mobilenet_v2(pretrained=True)
        self.model.classifier[1] = nn.Linear(self.model.classifier[1].in_features, num_classes)
    
    def forward(self, x):
        return self.model(x)

# 기본 변환
def get_transform():
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

def predict_face_type(image_path, model_instance=None):
    """얼굴 이미지를 분석하여 얼굴 유형 예측
    
    Args:
        image_path (str): 이미지 파일 경로
        model_instance: FaceModel 인스턴스(선택사항)
    
    Returns:
        list: 예측 결과 리스트 [{'class': 클래스명, 'probability': 확률}, ...]
    """
    from .models import FaceModel, FaceType
    
    # 활성화된 모델 선택 (모델 인스턴스가 전달되지 않은 경우)
    if model_instance is None:
        model_instance = FaceModel.objects.filter(is_active=True).first()
        
        if model_instance is None:
            raise ValueError("활성화된 모델이 없습니다. 관리자 페이지에서 모델을 등록하고 활성화하세요.")
    
    # 해당 모델의 유형 정보 로드
    face_types = list(FaceType.objects.filter(model=model_instance))
    
    if not face_types:
        raise ValueError(f"모델 '{model_instance.name}'에 등록된 얼굴 유형이 없습니다.")
    
    # 클래스 매핑 생성
    class_to_idx = {face_type.code: idx for idx, face_type in enumerate(face_types)}
    idx_to_class = {idx: face_type.code for idx, face_type in enumerate(face_types)}
    
    # CUDA 지원 확인
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    try:
        # 모델 파일 경로
        model_path = os.path.join(settings.MEDIA_ROOT, str(model_instance.model_file))
        
        # 모델 로드
        checkpoint = torch.load(model_path, map_location=device)
        
        # 모델 초기화
        pytorch_model = FaceModel(len(class_to_idx))
        pytorch_model.load_state_dict(checkpoint['model_state_dict'])
        pytorch_model.to(device)
        pytorch_model.eval()
        
        # 이미지 전처리
        transform = get_transform()
        image = Image.open(image_path).convert('RGB')
        image_tensor = transform(image).unsqueeze(0).to(device)
        
        # 예측
        with torch.no_grad():
            outputs = pytorch_model(image_tensor)
            probs = torch.nn.functional.softmax(outputs, dim=1)[0]
        
        # 결과 정렬
        probs_np = probs.cpu().numpy()
        indices = np.argsort(probs_np)[::-1]
        
        # 결과 생성
        results = []
        for i in indices:
            class_name = idx_to_class[i]
            probability = float(probs_np[i])
            
            # 해당 클래스에 맞는 FaceType 객체 찾기
            face_type = next((ft for ft in face_types if ft.code == class_name), None)
            
            result = {
                'class': class_name,
                'probability': probability
            }
            
            # FaceType 정보 추가
            if face_type:
                result['face_type_id'] = face_type.id
                result['face_type_name'] = face_type.name
                result['description'] = face_type.description
                result['characteristics'] = face_type.get_characteristics_list()
            
            results.append(result)
        
        return results
        
    except Exception as e:
        import traceback
        print(f"예측 중 오류 발생: {str(e)}")
        print(traceback.format_exc())
        raise