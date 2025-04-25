from django.shortcuts import render
from psychotest.models import Test
from facetest.models import FaceTestModel

def root(request):
    """메인 페이지"""
    # 최신 심리 테스트 가져오기
    recent_tests = Test.objects.all().order_by('-created_at')[:6]
    
    # 인기 테스트 가져오기 (조회수 기준)
    popular_tests = Test.objects.all().order_by('-view_count')[:6]
    
    # 최신 얼굴상 테스트 가져오기
    recent_face_tests = FaceTestModel.objects.filter(is_active=True).order_by('-created_at')[:6]
    
    context = {
        'recent_tests': recent_tests,
        'popular_tests': popular_tests,
        'recent_face_tests': recent_face_tests,
    }
    
    return render(request, 'root.html', context)