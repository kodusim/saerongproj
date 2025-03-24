from django.shortcuts import render
from psychotest.models import Test


def root(request):
    """메인 페이지"""
    # 심리테스트 목록 불러오기 (최신 6개)
    recent_tests = Test.objects.all().order_by('-created_at')[:6]
    
    return render(request, 'root.html', {
        'recent_tests': recent_tests,
    })