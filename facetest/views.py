from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
import json

from .models import FaceTestModel, FaceResultType, FaceResultImage

# 기존 index 뷰는 그대로 유지
def index(request):
    """얼굴상 테스트 메인 페이지"""
    face_test = FaceTestModel.objects.filter(is_active=True).first()
    return render(request, 'facetest/index.html', {'face_test': face_test})

# 관리자용 테스트 관리 페이지
@staff_member_required
def manage_test(request, test_id):
    """테스트 및 결과 유형 관리 페이지"""
    test = get_object_or_404(FaceTestModel, id=test_id)
    result_types = test.result_types.all().order_by('type_id')
    
    return render(request, 'facetest/admin/manage_test.html', {
        'test': test,
        'result_types': result_types,
    })

# 결과 유형 수정 API
@staff_member_required
@require_POST
def update_result_type(request, type_id):
    """결과 유형 정보 업데이트 API"""
    result_type = get_object_or_404(FaceResultType, id=type_id)
    
    try:
        data = json.loads(request.body)
        
        with transaction.atomic():
            # 기본 정보 업데이트
            if 'name' in data:
                result_type.name = data['name']
            if 'description' in data:
                result_type.description = data['description']
            
            # 특성 업데이트
            if 'characteristics' in data:
                characteristics = data['characteristics']
                result_type.characteristics = json.dumps(characteristics, ensure_ascii=False)
            
            # 예시 업데이트
            if 'examples' in data:
                examples = data['examples']
                result_type.examples = json.dumps(examples, ensure_ascii=False)
            
            result_type.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# 이미지 업로드 처리
@staff_member_required
@require_POST
def upload_result_image(request, type_id):
    """결과 유형 이미지 업로드"""
    result_type = get_object_or_404(FaceResultType, id=type_id)
    
    try:
        image = request.FILES.get('image')
        if not image:
            return JsonResponse({'success': False, 'error': '이미지가 제공되지 않았습니다.'}, status=400)
        
        title = request.POST.get('title', '')
        is_main = request.POST.get('is_main') == 'true'
        order = request.POST.get('order', 0)
        
        # 이미지 생성
        result_image = FaceResultImage.objects.create(
            result_type=result_type,
            image=image,
            title=title,
            is_main=is_main,
            order=order
        )
        
        # 대표 이미지 설정 시 다른 이미지들의 대표 상태 해제
        if is_main:
            FaceResultImage.objects.filter(
                result_type=result_type, 
                is_main=True
            ).exclude(id=result_image.id).update(is_main=False)
        
        return JsonResponse({
            'success': True,
            'image_id': result_image.id,
            'image_url': result_image.image.url
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# 이미지 삭제 처리
@staff_member_required
@require_POST
def delete_result_image(request, image_id):
    """결과 유형 이미지 삭제"""
    image = get_object_or_404(FaceResultImage, id=image_id)
    
    try:
        image.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)