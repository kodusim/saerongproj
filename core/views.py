from django.shortcuts import render
from psychotest.models import Test

from django.shortcuts import render
# 명시적으로 올바른 모델 임포트
from psychotest.models import Test


def root(request):
    """메인 페이지"""
    # 먼저 테스트가 있는지 확인
    test_count = Test.objects.all().count()
    print(f"DEBUG: 데이터베이스에 있는 테스트 수: {test_count}")

    # 최신 테스트 가져오기
    recent_tests = list(Test.objects.all().order_by('-created_at')[:6])
    print(f"DEBUG: 가져온 최신 테스트 수: {len(recent_tests)}")
    
    for test in recent_tests:
        print(f"DEBUG: 테스트 ID={test.id}, 제목={test.title}")
    
    context = {
        'recent_tests': recent_tests,
        'test_count': test_count,  # 디버깅용 추가 정보
    }
    
    # 템플릿에 명시적으로 전달
    response = render(request, 'root.html', context)
    return response