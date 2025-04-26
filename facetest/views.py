from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q
import json

from .models import FaceTestModel, FaceResultType, FaceResultImage

# 기존 index 뷰는 그대로 유지

def index(request):
    """얼굴상 테스트 메인 페이지"""
    # 활성화된 얼굴상 테스트 목록 가져오기
    face_tests = FaceTestModel.objects.filter(is_active=True)
    
    # 기본으로 보여줄 테스트 (첫 번째 테스트)
    test = face_tests.first()
    
    return render(request, 'facetest/index.html', {
        'face_tests': face_tests,
        'test': test
    })

def test_view(request, test_id):
    """특정 얼굴상 테스트 페이지"""
    # 특정 테스트 가져오기
    test = get_object_or_404(FaceTestModel, id=test_id, is_active=True)
    
    # 조회수 증가
    test.increase_view_count()
    
    # 다른 테스트 목록 (현재 테스트 제외)
    face_tests = FaceTestModel.objects.filter(is_active=True).exclude(id=test_id)
    
    return render(request, 'facetest/index.html', {
        'face_tests': face_tests,
        'test': test
    })

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

# 결과 유형 정보 가져오기 API
@staff_member_required
@require_http_methods(["GET"])
def get_result_type_info(request, type_id):
    """결과 유형 정보 가져오기 API"""
    result_type = get_object_or_404(FaceResultType, id=type_id)
    
    return JsonResponse({
        'success': True,
        'name': result_type.name,
        'description': result_type.description,
        'characteristics': result_type.get_characteristics_list(),
        'examples': result_type.get_examples_list()
    })

# 결과 유형 수정 API
@staff_member_required
@require_POST
def update_result_type(request, type_id):
    """결과 유형 정보 업데이트 API"""
    result_type = get_object_or_404(FaceResultType, id=type_id)
    
    try:
        # JSON 데이터 파싱
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'JSON 형식이 잘못되었습니다.'}, status=400)
        
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
        
        try:
            order = int(order)
        except (ValueError, TypeError):
            order = 0
        
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

# 대표 이미지 설정
@staff_member_required
@require_POST
def set_main_image(request, image_id):
    """대표 이미지 설정"""
    image = get_object_or_404(FaceResultImage, id=image_id)
    result_type = image.result_type
    
    try:
        with transaction.atomic():
            # 모든 이미지 대표 상태 해제
            FaceResultImage.objects.filter(
                result_type=result_type, 
                is_main=True
            ).update(is_main=False)
            
            # 현재 이미지 대표로 설정
            image.is_main = True
            image.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# 결과 유형 일괄 관리 페이지
@staff_member_required
def bulk_manage_result_types(request, test_id):
    """모든 결과 유형을 한 페이지에서 관리하는 뷰"""
    test = get_object_or_404(FaceTestModel, id=test_id)
    result_types = test.result_types.all().order_by('type_id')
    
    return render(request, 'admin/facetest/bulk_manage.html', {
        'test': test,
        'result_types': result_types,
        'opts': FaceTestModel._meta,
        'title': f"{test.name} - 결과 유형 통합 관리",
    })

def analyze_face(request):
    """얼굴 이미지 분석 처리"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '잘못된 요청 방식입니다.'})
    
    try:
        # 이미지 파일 받기
        image_file = request.FILES.get('image')
        if not image_file:
            return JsonResponse({'success': False, 'error': '이미지 파일이 제공되지 않았습니다.'})
        
        # 파일 타입 확인
        if not image_file.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            return JsonResponse({'success': False, 'error': '지원되지 않는 파일 형식입니다. JPG, PNG 파일만 업로드 가능합니다.'})
        
        # 파일 크기 확인 (5MB 제한)
        if image_file.size > 5 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': '파일 크기가 너무 큽니다. 5MB 이하의 파일을 선택해주세요.'})
        
        # 세션에 임시 파일 경로 저장
        import os
        from django.conf import settings
        import uuid
        
        # 임시 폴더에 파일 저장
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # 고유한 파일 이름 생성
        file_ext = os.path.splitext(image_file.name)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(temp_dir, unique_filename)
        
        # 파일 저장
        with open(file_path, 'wb+') as destination:
            for chunk in image_file.chunks():
                destination.write(chunk)
        
        # 세션에 파일 경로 저장
        request.session['face_image_path'] = os.path.join('temp', unique_filename)
        
        # 모델 로드하고 이미지 분석
        face_test = FaceTestModel.objects.filter(is_active=True).first()
        
        if not face_test:
            return JsonResponse({'success': False, 'error': '활성화된 얼굴 분석 모델이 없습니다.'})
            
        # 모델 파일과 결과 유형 파일 경로 가져오기
        model_path = face_test.model_file.path
        result_types_path = face_test.result_types_file.path
        
        # predict.py 스크립트 실행 (파일이 있는 경우)
        if face_test.predict_script:
            try:
                import subprocess
                
                # 예측 스크립트 경로
                predict_script_path = face_test.predict_script.path
                
                # 스크립트 실행
                result = subprocess.run(
                    ['python', predict_script_path, file_path, model_path, result_types_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print("예측 스크립트 오류:", result.stderr)
                    raise Exception(f"예측 스크립트 실행 오류: {result.stderr}")
                
                # 스크립트 출력 결과 파싱
                import json
                prediction_result = json.loads(result.stdout)
                
                # 결과 유형 ID 가져오기
                prediction_id = prediction_result.get('type_id', 0)
                
                # 해당 유형 ID로 결과 유형 찾기
                result_type = face_test.result_types.filter(type_id=prediction_id).first()
                
            except Exception as e:
                print(f"모델 실행 중 오류: {str(e)}")
                # 오류 발생 시 랜덤하게 결과 유형 선택 (대체 방안)
                import random
                result_types = list(face_test.result_types.all())
                result_type = random.choice(result_types) if result_types else None
        else:
            # predict_script가 없는 경우 랜덤 결과 반환 (테스트용)
            import random
            result_types = list(face_test.result_types.all())
            result_type = random.choice(result_types) if result_types else None
        
        if result_type:
            # 세션에 결과 저장
            request.session['face_result'] = {
                'test_id': face_test.id,
                'result_type_id': result_type.id
            }
            
            # 결과 페이지 URL 반환
            return JsonResponse({
                'success': True,
                'result_url': reverse('facetest:result')
            })
        
        return JsonResponse({'success': False, 'error': '얼굴상 분석에 실패했습니다. 다른 사진을 시도해보세요.'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'이미지 처리 중 오류가 발생했습니다: {str(e)}'})


def result(request):
    """얼굴상 분석 결과 페이지"""
    # 세션에서 결과 데이터 가져오기
    result_data = request.session.get('face_result')
    
    if not result_data:
        # 결과 데이터가 없으면 임시 더미 데이터 생성 (개발용)
        # 실제 서비스에서는 결과가 없을 경우 메인 페이지로 리다이렉트
        # return redirect('facetest:index')
        
        # 개발용 임시 데이터 
        face_test = FaceTestModel.objects.filter(is_active=True).first()
        if face_test:
            result_type = face_test.result_types.first()
            if result_type:
                result_data = {
                    'test_id': face_test.id,
                    'result_type_id': result_type.id
                }
    
    # 결과 데이터로 상세 정보 조회
    face_test = None
    result_type = None
    
    if result_data:
        try:
            face_test = FaceTestModel.objects.get(id=result_data['test_id'])
            result_type = FaceResultType.objects.get(id=result_data['result_type_id'])
        except (FaceTestModel.DoesNotExist, FaceResultType.DoesNotExist):
            pass
    
    # 이미지 경로 가져오기
    face_image_path = request.session.get('face_image_path')
    face_image_url = None
    
    if face_image_path:
        from django.conf import settings
        face_image_url = f"{settings.MEDIA_URL}{face_image_path}"
    
    # 다른 얼굴상 테스트 목록
    other_tests = FaceTestModel.objects.filter(is_active=True)
    if face_test:
        other_tests = other_tests.exclude(id=face_test.id)
    other_tests = other_tests[:4]  # 최대 4개만 표시
    
    # 카카오 API 키 가져오기
    from django.conf import settings
    kakao_api_key = getattr(settings, 'KAKAO_JAVASCRIPT_KEY', '')
    
    context = {
        'face_test': face_test,
        'result_type': result_type,
        'face_image_url': face_image_url,
        'other_tests': other_tests,
        'characteristics': result_type.get_characteristics_list() if result_type else [],
        'examples': result_type.get_examples_list() if result_type else [],
        'kakao_api_key': kakao_api_key
    }
    
    return render(request, 'facetest/result.html', context)

def test_intro(request, test_id):
    """테스트 인트로 페이지 - 시작 화면 보여주기"""
    test = get_object_or_404(FaceTestModel, id=test_id, is_active=True)
    
    # 조회수 증가
    test.increase_view_count()
    
    return render(request, 'facetest/test_intro.html', {'test': test})

def test_list(request):
    """얼굴상 테스트 목록 페이지"""
    # 검색 기능 구현
    search_query = request.GET.get('search', '')
    if search_query:
        tests = FaceTestModel.objects.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query),
            is_active=True
        ).order_by('-created_at')
    else:
        tests = FaceTestModel.objects.filter(is_active=True).order_by('-created_at')
    
    # 페이지네이션 구현
    paginator = Paginator(tests, 9)  # 한 페이지에 9개씩 표시
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'tests': page_obj,
        'search_query': search_query,
        'is_paginated': page_obj.has_other_pages(),
        'paginator': paginator,
        'page_obj': page_obj,
    }
    
    return render(request, 'facetest/test_list.html', context)