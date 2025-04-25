import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.contrib import messages

from .models import FaceModel, FaceType, FaceTestResult
from .forms import FaceImageUploadForm
from .predict import predict_face_type

def index(request):
    """얼굴테스트 메인 페이지"""
    # 가장 최근에 활성화된 모델 가져오기
    model = FaceModel.objects.filter(is_active=True).first()
    
    if not model:
        # 사용 가능한 모델이 없으면 메시지 표시
        messages.warning(request, "현재 얼굴테스트를 사용할 수 없습니다. 관리자에게 문의하세요.")
    
    # 얼굴 유형 목록
    face_types = []
    if model:
        face_types = FaceType.objects.filter(model=model)
    
    # 이미지 업로드 폼
    form = FaceImageUploadForm()
    
    context = {
        'form': form,
        'model': model,
        'face_types': face_types,
    }
    
    return render(request, 'facetest/index.html', context)

def upload_image(request):
    """이미지 업로드 및 분석"""
    if request.method != 'POST':
        return redirect('facetest:index')
    
    form = FaceImageUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "올바른 이미지 파일을 업로드해주세요.")
        return redirect('facetest:index')
    
    # 활성화된 모델 가져오기
    model = FaceModel.objects.filter(is_active=True).first()
    if not model:
        messages.error(request, "현재 얼굴테스트를 사용할 수 없습니다.")
        return redirect('facetest:index')
    
    try:
        # 이미지 저장 (임시)
        image = form.cleaned_data['image']
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"temp_{image.name}")
        
        with open(temp_path, 'wb+') as f:
            for chunk in image.chunks():
                f.write(chunk)
        
        # 이미지 분석
        results = predict_face_type(temp_path, model)
        
        if not results:
            messages.error(request, "얼굴 분석에 실패했습니다. 다른 이미지를 시도해보세요.")
            # 임시 파일 삭제
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return redirect('facetest:index')
        
        # 최고 결과 가져오기
        top_result = results[0]
        face_type = get_object_or_404(FaceType, model=model, code=top_result['class'])
        
        # 결과 저장
        test_result = FaceTestResult(
            image=image,
            face_type=face_type,
            probability=top_result['probability'],
            all_results=results
        )
        test_result.save()
        
        # 임시 파일 삭제
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # 결과 페이지로 리다이렉트
        return redirect('facetest:result_detail', test_result.id)
        
    except Exception as e:
        # 오류 처리
        import traceback
        print(f"얼굴 분석 중 오류 발생: {str(e)}")
        print(traceback.format_exc())
        
        messages.error(request, f"얼굴 분석 중 오류가 발생했습니다: {str(e)}")
        return redirect('facetest:index')

def result_detail(request, result_id):
    """테스트 결과 상세 페이지"""
    result = get_object_or_404(FaceTestResult, id=result_id)
    
    # 얼굴 유형 정보
    face_type = result.face_type
    
    # 모든 결과 (상위 3개만)
    all_results = []
    if result.all_results:
        # 결과가 리스트인 경우
        if isinstance(result.all_results, list):
            all_results = result.all_results[:3]
        # 결과가 딕셔너리인 경우
        elif isinstance(result.all_results, dict):
            for key, value in result.all_results.items():
                if isinstance(value, dict) and 'probability' in value:
                    all_results.append(value)
            # 확률 기준으로 정렬
            all_results = sorted(all_results, key=lambda x: x.get('probability', 0), reverse=True)[:3]
    
    # 관련 얼굴 유형
    related_types = None
    if result.face_type.model:
        related_types = FaceType.objects.filter(model=result.face_type.model)
    
    # 공유 URL
    share_url = request.build_absolute_uri(reverse('facetest:share_result', args=[result.id]))
    
    context = {
        'result': result,
        'face_type': face_type,
        'all_results': all_results,
        'related_types': related_types,
        'share_url': share_url,
        'kakao_api_key': getattr(settings, 'KAKAO_JAVASCRIPT_KEY', '')
    }
    
    return render(request, 'facetest/result_detail.html', context)

def share_result(request, result_id):
    """결과 공유 페이지 (소셜 미디어 공유용)"""
    result = get_object_or_404(FaceTestResult, id=result_id)
    
    context = {
        'result': result,
        'face_type': result.face_type,
        'is_shared_view': True,
        'kakao_api_key': getattr(settings, 'KAKAO_JAVASCRIPT_KEY', '')
    }
    
    return render(request, 'facetest/share_result.html', context)