from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Test, Question, Option, Result, Category, SharedTestResult
from django.conf import settings
from django.template.loader import render_to_string

def test_list(request):
    """테스트 목록 페이지"""
    # 검색 기능 구현
    search_query = request.GET.get('search', '')
    if search_query:
        tests = Test.objects.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        ).order_by('-created_at')
    else:
        tests = Test.objects.all().order_by('-created_at')
    
    # 페이지네이션 구현
    paginator = Paginator(tests, 9)  # 한 페이지에 9개씩 표시 (3x3 그리드)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'tests': page_obj,
        'search_query': search_query,
        'is_paginated': page_obj.has_other_pages(),
        'paginator': paginator,
        'page_obj': page_obj,
    }
    
    return render(request, 'psychotest/test_list.html', context)


def test_detail(request, test_id):
    """테스트 상세 페이지"""
    test = get_object_or_404(Test, id=test_id)
    # 조회수 증가
    test.increase_view_count()
    return render(request, 'psychotest/test_detail.html', {'test': test})

def test_intro(request, test_id):
    """테스트 인트로 페이지 - 시작 화면 보여주기"""
    test = get_object_or_404(Test, id=test_id)
    # 조회수 증가
    test.increase_view_count()
    
    # 카카오 API 키 가져오기
    from django.conf import settings
    kakao_api_key = getattr(settings, 'KAKAO_JAVASCRIPT_KEY', '')
    
    return render(request, 'psychotest/test_intro.html', {
        'test': test,
        'kakao_api_key': kakao_api_key
    })

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
        
        # 공유 가능한 영구 결과 생성
        if result:
            shared_result = SharedTestResult.objects.create(
                test=test,
                result=result,
                score=total_score,
                calculation_method='sum'
            )
            request.session['shared_result_id'] = str(shared_result.id)
        
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
        
        # 공유 가능한 영구 결과 생성
        if result:
            shared_result = SharedTestResult.objects.create(
                test=test,
                result=result,
                category=max_category,
                category_scores=category_scores,
                calculation_method='category'
            )
            request.session['shared_result_id'] = str(shared_result.id)
    
    else:  # pattern 방식은 추후 구현
        # 기본 결과 선택
        result = Result.objects.filter(test=test).first()
        request.session['test_result'] = {
            'test_id': test.id,
            'result_id': result.id if result else None,
            'method': 'pattern'
        }
        
        # 공유 가능한 영구 결과 생성
        if result:
            shared_result = SharedTestResult.objects.create(
                test=test,
                result=result,
                calculation_method='pattern'
            )
            request.session['shared_result_id'] = str(shared_result.id)
    
    request.session.modified = True
    
    return redirect('psychotest:test_result', test_id=test.id)


def test_result(request, test_id):
    """테스트 결과 페이지"""
    test = get_object_or_404(Test, id=test_id)
    
    # URL 파라미터로 특정 결과 ID가 전달되었는지 확인
    result_id = request.GET.get('result_id')
    result = None
    
    if result_id:
        # 특정 결과 ID가 전달된 경우, 해당 결과를 표시
        try:
            result = Result.objects.get(id=result_id, test=test)
        except Result.DoesNotExist:
            messages.error(request, "요청한 결과를 찾을 수 없습니다.")
    else:
        # 세션에서 공유 결과 ID 확인
        shared_result_id = request.session.get('shared_result_id')
        shared_result = None
        
        if shared_result_id:
            try:
                shared_result = SharedTestResult.objects.get(id=shared_result_id)
                result = shared_result.result
            except (SharedTestResult.DoesNotExist, ValueError):
                pass
        
        # 세션에서 결과 데이터 가져오기
        if not result:
            result_data = request.session.get('test_result', {})
            
            if not result_data or int(result_data.get('test_id', 0)) != test.id:
                messages.warning(request, "테스트 결과가 없습니다. 테스트를 다시 진행해주세요.")
                return redirect('psychotest:take_test', test_id=test.id)
            
            result_id = result_data.get('result_id')
            if result_id:
                result = get_object_or_404(Result, id=result_id)
    
    # 이미지 크기 측정 (선택적)
    image_dimensions = {}
    if result and result.image:
        try:
            from PIL import Image
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
    
    # 카카오 API 키 가져오기
    kakao_api_key = getattr(settings, 'KAKAO_JAVASCRIPT_KEY', '')
    
    # 해당 테스트의 모든 결과 가져오기 (모달용)
    all_results = Result.objects.filter(test=test)

    context = {
        'test': test,
        'result': result,
        'all_results': all_results,
        'image_dimensions': image_dimensions,
        'kakao_api_key': kakao_api_key,
        'shared_result': shared_result if 'shared_result' in locals() else None,
    }
    
    # 결과 표시 후 필요 없는 테스트 답변 데이터 정리
    if 'test_answers' in request.session and str(test_id) in request.session['test_answers']:
        del request.session['test_answers'][str(test_id)]
        request.session.modified = True
    
    return render(request, 'psychotest/test_result.html', context)


def shared_result(request, result_id):
    """공유된 테스트 결과 페이지"""
    shared_result = get_object_or_404(SharedTestResult, id=result_id)
    test = shared_result.test
    result = shared_result.result
    
    # 이미지 크기 측정 (선택적)
    image_dimensions = {}
    if result and result.image:
        try:
            from PIL import Image
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
    
    # 카카오 API 키 가져오기
    kakao_api_key = getattr(settings, 'KAKAO_JAVASCRIPT_KEY', '')
    
    # 결과 데이터 구성
    result_data = {
        'test_id': test.id,
        'result_id': result.id,
        'score': shared_result.score,
        'category': shared_result.category,
        'category_scores': shared_result.category_scores,
        'method': shared_result.calculation_method
    }
    
    # 해당 테스트의 모든 결과 가져오기 (모달용)
    all_results = Result.objects.filter(test=test)
    
    context = {
        'test': test,
        'result': result,
        'result_data': result_data,
        'image_dimensions': image_dimensions,
        'kakao_api_key': kakao_api_key,
        'shared_result': shared_result,
        'is_shared_view': True,  # 공유된 결과 페이지임을 표시
        'all_results': all_results,  # 모든 결과 추가
    }
    
    # 메타 태그를 위한 HTML 코드
    if result.image:
        image_url = request.build_absolute_uri(result.image.url)
        title = f"{result.title} - {test.title} | 새롱"
        description = result.description[:150] if result.description else ""
        
        # HTML 직접 렌더링
        html = render_to_string('psychotest/test_result.html', context, request)
        
        # 메타 태그 삽입 - head 태그 바로 뒤에 추가
        meta_tags = f"""
        <meta property="og:title" content="{title}" />
        <meta property="og:description" content="{description}" />
        <meta property="og:url" content="{request.build_absolute_uri()}" />
        <meta property="og:image" content="{image_url}" />
        <meta property="twitter:card" content="summary_large_image" />
        <meta property="twitter:title" content="{title}" />
        <meta property="twitter:description" content="{description}" />
        <meta property="twitter:image" content="{image_url}" />
        """
        
        # head 태그 뒤에 메타 태그 삽입
        html = html.replace('<head>', '<head>' + meta_tags)
        
        return HttpResponse(html)
    else:
        return render(request, 'psychotest/test_result.html', context)