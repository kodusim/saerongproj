from django.shortcuts import render
from psychotest.models import Test
from facetest.models import FaceTestModel

def root(request):
    """메인 페이지"""
    # 최신 심리 테스트 가져오기
    recent_tests = Test.objects.all().order_by('-created_at')[:6]
    
    # 최신 얼굴상 테스트 가져오기
    recent_face_tests = FaceTestModel.objects.filter(is_active=True).order_by('-created_at')[:6]
    
    # 인기 테스트 가져오기 (심리 테스트와 얼굴상 테스트 통합하여 조회수 기준)
    # 먼저 각 테스트 타입별로 가져온 후 결합
    popular_psycho_tests = Test.objects.all().order_by('-view_count')[:10]
    popular_face_tests = FaceTestModel.objects.filter(is_active=True).order_by('-view_count')[:10]
    
    # 통합 인기 테스트 리스트 생성 (각 테스트에 유형 정보 추가)
    combined_popular = []
    
    for test in popular_psycho_tests:
        combined_popular.append({
            'id': test.id,
            'title': test.title,
            'image': test.image,
            'view_count': test.view_count,
            'type': 'psycho',
            'obj': test
        })
    
    for test in popular_face_tests:
        combined_popular.append({
            'id': test.id,
            'title': test.name,
            'image': test.image,
            'view_count': test.view_count,
            'type': 'face',
            'obj': test
        })
    
    # 조회수 기준 정렬 후 상위 6개 선택
    popular_tests = sorted(combined_popular, key=lambda x: x['view_count'], reverse=True)[:6]
    
    context = {
        'recent_tests': recent_tests,
        'recent_face_tests': recent_face_tests,
        'popular_tests': popular_tests,
    }
    
    return render(request, 'root.html', context)