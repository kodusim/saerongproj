from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from .models import Test, Question, Option, Result


def test_list(request):
    """테스트 목록 페이지"""
    tests = Test.objects.all()
    return render(request, 'psychotest/test_list.html', {'tests': tests})


def test_detail(request, test_id):
    """테스트 상세 페이지"""
    test = get_object_or_404(Test, id=test_id)
    return render(request, 'psychotest/test_detail.html', {'test': test})


def take_test(request, test_id):
    """테스트 진행 페이지"""
    test = get_object_or_404(Test, id=test_id)
    questions = test.questions.all().prefetch_related('options')
    
    if request.method == 'POST':
        # 테스트 결과 계산 (간단한 구현)
        total_score = 0
        
        # 결과 페이지로 리다이렉트
        return redirect('psychotest:test_result', test_id=test.id)
    
    return render(request, 'psychotest/take_test.html', {
        'test': test,
        'questions': questions,
    })


def test_result(request, test_id):
    """테스트 결과 페이지"""
    test = get_object_or_404(Test, id=test_id)
    # 실제로는 계산된 점수에 따라 결과를 보여줘야 함
    # 지금은 예시로 첫 번째 결과를 보여줌
    result = test.results.first()
    
    return render(request, 'psychotest/test_result.html', {
        'test': test,
        'result': result,
    })