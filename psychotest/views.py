from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from .models import Test, Question, Option, Result, Category
from django.http import HttpResponse
from django.conf import settings

def test_list(request):
    """테스트 목록 페이지"""
    tests = Test.objects.all()
    return render(request, 'psychotest/test_list.html', {'tests': tests})


def test_detail(request, test_id):
    """테스트 상세 페이지"""
    test = get_object_or_404(Test, id=test_id)
    # 조회수 증가
    test.increase_view_count()
    return render(request, 'psychotest/test_detail.html', {'test': test})

def test_intro(request, test_id):
    """테스트 인트로 페이지 - 시작 화면 보여주기"""
    test = get_object_or_404(Test, id=test_id)
    # 조회수 증가는 여기서 처리하고 test_detail에서는 제거
    test.increase_view_count()
    return render(request, 'psychotest/test_intro.html', {'test': test})

def take_test(request, test_id):
    """테스트 진행 페이지"""
    test = get_object_or_404(Test, id=test_id)
    questions = test.questions.all().prefetch_related('options')
    
    if not questions.exists():
        messages.warning(request, "이 테스트에는 아직 질문이 없습니다.")
        return redirect('psychotest:test_detail', test_id=test.id)
    
    # 세션에서 테스트 응답 초기화
    if 'test_answers' in request.session:
        if str(test_id) in request.session['test_answers']:
            del request.session['test_answers'][str(test_id)]
            request.session.modified = True
    
    if 'test_answers' not in request.session:
        request.session['test_answers'] = {}
    request.session.modified = True
    
    if test.view_style == 'one':
        # 한 질문씩 보여주기
        first_question = questions.first()
        total_questions = questions.count()
        
        return render(request, 'psychotest/question_single.html', {
            'test': test,
            'question': first_question,
            'current_index': 1,
            'total_questions': total_questions,
            'progress': int((1 / total_questions) * 100)
        })
    else:
        # 모든 질문 한 번에 보여주기
        if request.method == 'POST':
            # 테스트 결과 계산
            answers = {}
            for question in questions:
                answer_key = f'question_{question.id}'
                if answer_key in request.POST:
                    option_id = request.POST.get(answer_key)
                    answers[str(question.id)] = option_id
            
            # 세션에 답변 저장
            request.session['test_answers'][str(test_id)] = answers
            request.session.modified = True
            
            # 결과 페이지로 리다이렉트
            return redirect('psychotest:calculate_result', test_id=test.id)
        
        return render(request, 'psychotest/take_test.html', {
            'test': test,
            'questions': questions,
        })


def answer_question(request, test_id, question_id):
    """HTMX로 단일 질문에 대한 응답 처리"""
    test = get_object_or_404(Test, id=test_id)
    current_question = get_object_or_404(Question, id=question_id)
    
    if request.method == 'POST':
        option_id = request.POST.get('answer')
        current_index = int(request.POST.get('current_index'))
        
        # 세션에 답변 저장
        if 'test_answers' not in request.session:
            request.session['test_answers'] = {}
        if str(test_id) not in request.session['test_answers']:
            request.session['test_answers'][str(test_id)] = {}
        
        request.session['test_answers'][str(test_id)][str(question_id)] = option_id
        request.session.modified = True
        
        # 다음 질문 찾기
        next_question = Question.objects.filter(
            test=test, 
            order__gt=current_question.order
        ).order_by('order').first()
        
        total_questions = test.questions.count()
        
        if next_question:
            # 다음 질문으로
            next_index = current_index + 1
            progress = int((next_index / total_questions) * 100)
            
            # HTMX 요청인 경우 부분 템플릿만 반환
            if request.headers.get('HX-Request'):
                return render(request, 'psychotest/partials/question.html', {
                    'test': test,
                    'question': next_question,
                    'current_index': next_index,
                    'total_questions': total_questions,
                    'progress': progress
                })
            else:
                # 일반 요청인 경우 전체 페이지 반환
                return render(request, 'psychotest/question_single.html', {
                    'test': test,
                    'question': next_question,
                    'current_index': next_index,
                    'total_questions': total_questions,
                    'progress': progress
                })
        else:
            # 결과 계산 및 리다이렉트
            # HTMX 요청인 경우 HX-Redirect 헤더 사용
            if request.headers.get('HX-Request'):
                from django.urls import reverse
                response = HttpResponse()
                response['HX-Redirect'] = reverse('psychotest:calculate_result', args=[test_id])
                return response
            else:
                return redirect('psychotest:calculate_result', test_id=test.id)


def calculate_result(request, test_id):
    """테스트 결과 계산 및 결과 페이지로 리다이렉트"""
    test = get_object_or_404(Test, id=test_id)
    
    # 세션에서 답변 가져오기
    if 'test_answers' not in request.session or str(test_id) not in request.session['test_answers']:
        messages.error(request, "테스트 응답이 없습니다. 테스트를 다시 시작해주세요.")
        return redirect('psychotest:take_test', test_id=test_id)
    
    answers = request.session['test_answers'][str(test_id)]
    
    # 계산 방식에 따라 결과 도출
    if test.calculation_method == 'sum':
        # 점수 합산 방식
        total_score = 0
        for question_id, option_id in answers.items():
            try:
                option = Option.objects.get(id=option_id)
                total_score += option.score
            except Option.DoesNotExist:
                pass
        
        # 점수에 맞는 결과 찾기
        result = Result.objects.filter(
            test=test,
            min_score__lte=total_score,
            max_score__gte=total_score
        ).first()
        
        # 결과가 없으면 가장 가까운 결과 선택
        if not result:
            result = Result.objects.filter(test=test).order_by('min_score').first()
        
        # 세션에 결과 저장
        request.session['test_result'] = {
            'test_id': test.id,
            'result_id': result.id if result else None,
            'score': total_score,
            'method': 'sum'
        }
        
    elif test.calculation_method == 'category':
        # 카테고리 점수 방식
        category_scores = {}
        
        for question_id, option_id in answers.items():
            try:
                option = Option.objects.get(id=option_id)
                if option.category_scores:
                    for category, score in option.category_scores.items():
                        if category not in category_scores:
                            category_scores[category] = 0
                        category_scores[category] += score
            except Option.DoesNotExist:
                continue
        
        # 가장 높은 점수의 카테고리 찾기
        if category_scores:
            max_category = max(category_scores.items(), key=lambda x: x[1])[0]
            
            # 해당 카테고리에 맞는 결과 찾기
            result = Result.objects.filter(
                test=test,
                category=max_category
            ).first()
        else:
            max_category = None
            result = Result.objects.filter(test=test).first()
        
        # 세션에 결과 저장
        request.session['test_result'] = {
            'test_id': test.id,
            'result_id': result.id if result else None,
            'category': max_category,
            'category_scores': category_scores,
            'method': 'category'
        }
    
    else:  # pattern 방식은 추후 구현
        # 기본 결과 선택
        result = Result.objects.filter(test=test).first()
        request.session['test_result'] = {
            'test_id': test.id,
            'result_id': result.id if result else None,
            'method': 'pattern'
        }
    
    request.session.modified = True
    
    return redirect('psychotest:test_result', test_id=test.id)


def test_result(request, test_id):
    """테스트 결과 페이지"""
    test = get_object_or_404(Test, id=test_id)
    
    # 세션에서 결과 데이터 가져오기
    result_data = request.session.get('test_result', {})
    
    if not result_data or int(result_data.get('test_id', 0)) != test.id:
        messages.warning(request, "테스트 결과가 없습니다. 테스트를 다시 진행해주세요.")
        return redirect('psychotest:take_test', test_id=test.id)
    
    result_id = result_data.get('result_id')
    result = None
    if result_id:
        result = get_object_or_404(Result, id=result_id)
    
    # 이미지 크기 측정 (선택적)
    image_dimensions = {}
    if result and result.image:
        try:
            from PIL import Image
            from django.conf import settings
            import os
            
            img_path = os.path.join(settings.MEDIA_ROOT, result.image.name)
            with Image.open(img_path) as img:
                image_dimensions = {
                    'width': img.width,
                    'height': img.height,
                    'ratio': img.height / img.width
                }
        except Exception as e:
            # 오류 시 기본값 설정
            image_dimensions = {'width': 500, 'height': 705, 'ratio': 1.41}
    
    from django.conf import settings
    kakao_api_key = getattr(settings, '3fd3d8be1d733c63de14e57eeff76d66', '')

    context = {
        'test': test,
        'result': result,
        'result_data': result_data,
        'image_dimensions': image_dimensions,
        'kakao_api_key': kakao_api_key  # 컨텍스트에 API 키 추가
    }
    
    # 결과 표시 후 필요 없는 테스트 답변 데이터 정리
    if 'test_answers' in request.session and str(test_id) in request.session['test_answers']:
        del request.session['test_answers'][str(test_id)]
        request.session.modified = True
    
    return render(request, 'psychotest/test_result.html', context)