from django.shortcuts import render
from psychotest.models import Test

def root(request):
    """메인 페이지"""
    # 최신 테스트 가져오기
    recent_tests = Test.objects.all().order_by('-created_at')[:6]
    
    # 인기 테스트 가져오기 (조회수 기준)
    popular_tests = Test.objects.all().order_by('-view_count')[:6]
    
    context = {
        'recent_tests': recent_tests,
        'popular_tests': popular_tests,
    }
    
    return render(request, 'root.html', context)