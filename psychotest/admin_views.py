from django.views.generic import TemplateView
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.shortcuts import redirect
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import csv
import io
from django.db import transaction
from .models import Test, Question, Option, Result, Category

@method_decorator(staff_member_required, name='dispatch')
class TestWizardMethodSelectionView(TemplateView):
    """테스트 마법사의 첫 화면 - 계산 방식 선택"""
    template_name = 'admin/psychotest/test/wizard_method_selection.html'

@method_decorator(staff_member_required, name='dispatch')
class TestWizardSumView(TemplateView):
    """점수 합산 방식의 테스트 정보 입력 단계"""
    template_name = 'admin/psychotest/test/wizard_sum_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        # 폼 데이터 검증
        title = request.POST.get('title')
        description = request.POST.get('description')
        
        if not title or not description:
            messages.error(request, "제목과 설명은 필수 입력 항목입니다.")
            return self.render_to_response(self.get_context_data())
        
        # 세션에 테스트 정보 저장
        request.session['wizard_test_info'] = {
            'title': title,
            'description': description,
            'category_id': request.POST.get('category'),
            'calculation_method': 'sum',  # 점수 합산 방식 고정
            'view_style': 'one',  # 한 질문씩 보기 방식 고정
        }
        
        # 파일 업로드 처리
        if 'image' in request.FILES:
            image = request.FILES['image']
            path = f'temp/wizard/{request.session.session_key}/test_image{os.path.splitext(image.name)[1]}'
            if default_storage.exists(path):
                default_storage.delete(path)
            path = default_storage.save(path, ContentFile(image.read()))
            request.session['wizard_test_image_path'] = path
        
        if 'intro_image' in request.FILES:
            intro_image = request.FILES['intro_image']
            path = f'temp/wizard/{request.session.session_key}/intro_image{os.path.splitext(intro_image.name)[1]}'
            if default_storage.exists(path):
                default_storage.delete(path)
            path = default_storage.save(path, ContentFile(intro_image.read()))
            request.session['wizard_intro_image_path'] = path
        
        request.session.modified = True
        return redirect('admin:psychotest_test_wizard_sum_questions')
    
@method_decorator(staff_member_required, name='dispatch')
class TestWizardSumQuestionsView(TemplateView):
    """점수 합산 방식의 테스트 질문 입력 단계"""
    template_name = 'admin/psychotest/test/wizard_questions_form.html'
    
    def get(self, request, *args, **kwargs):
        if 'wizard_test_info' not in request.session:
            messages.warning(request, "테스트 정보를 먼저 입력해주세요.")
            return redirect('admin:psychotest_test_wizard_sum')
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        csv_file = request.FILES.get('csv_file')
        csv_content = request.POST.get('csv_content')
        
        if not csv_file and not csv_content:
            messages.error(request, "CSV 파일을 업로드해주세요.")
            return self.render_to_response(self.get_context_data())
        
        # CSV 파일 처리
        if csv_file:
            path = f'temp/wizard/{request.session.session_key}/questions.csv'
            if default_storage.exists(path):
                default_storage.delete(path)
            path = default_storage.save(path, ContentFile(csv_file.read()))
            request.session['wizard_csv_path'] = path
            
            if csv_content:
                try:
                    questions_data = self.parse_csv_content(csv_content)
                    request.session['wizard_questions_data'] = questions_data
                except Exception as e:
                    messages.error(request, f"CSV 파일 파싱 오류: {str(e)}")
                    return self.render_to_response(self.get_context_data())
                
        # 질문 이미지 처리
        question_images = {}
        for key, file in request.FILES.items():
            if key.startswith('question_image_'):
                question_index = key.replace('question_image_', '')
                path = f'temp/wizard/{request.session.session_key}/question_{question_index}{os.path.splitext(file.name)[1]}'
                if default_storage.exists(path):
                    default_storage.delete(path)
                path = default_storage.save(path, ContentFile(file.read()))
                question_images[question_index] = path
        
        if question_images:
            request.session['wizard_question_images'] = question_images
        
        request.session.modified = True
        return redirect('admin:psychotest_test_wizard_sum_results')
    
    def parse_csv_content(self, csv_content):
        """CSV 내용 파싱"""
        questions_data = []
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        if len(rows) < 2:
            raise ValueError("CSV 파일에 충분한 데이터가 없습니다.")
        
        header = rows[0]
        for i in range(1, len(header)):
            question_text = header[i].strip()
            if not question_text:
                continue
                
            options_data = []
            for row_idx, row in enumerate(rows[1:], 1):
                if len(row) <= i:
                    continue
                    
                option_text = row[i].strip()
                if not option_text:
                    continue
                    
                try:
                    option_score = int(row[0].strip()) if row[0].strip() else row_idx
                except (ValueError, IndexError):
                    option_score = row_idx
                
                options_data.append({
                    'text': option_text,
                    'score': option_score
                })
            
            if question_text and options_data:
                questions_data.append({
                    'text': question_text,
                    'order': i,
                    'options': options_data
                })
        
        return questions_data

@method_decorator(staff_member_required, name='dispatch')
class TestWizardSumResultsView(TemplateView):
    """점수 합산 방식의 테스트 결과 설정 단계"""
    template_name = 'admin/psychotest/test/wizard_results_form.html'
    
    def get(self, request, *args, **kwargs):
        if 'wizard_test_info' not in request.session or 'wizard_questions_data' not in request.session:
            messages.warning(request, "테스트 정보와 질문을 먼저 입력해주세요.")
            return redirect('admin:psychotest_test_wizard_sum')
        
        min_score, max_score = self.calculate_score_range(request.session['wizard_questions_data'])
        
        context = self.get_context_data(**kwargs)
        context['min_possible_score'] = min_score
        context['max_possible_score'] = max_score
        
        return self.render_to_response(context)
    
    def calculate_score_range(self, questions_data):
        """질문 데이터를 기반으로 최소/최대 가능 점수 계산"""
        min_score = 0
        max_score = 0
        
        for question in questions_data:
            min_option_score = float('inf')
            max_option_score = float('-inf')
            
            for option in question['options']:
                score = option['score']
                min_option_score = min(min_option_score, score)
                max_option_score = max(max_option_score, score)
            
            if min_option_score != float('inf'):
                min_score += min_option_score
            
            if max_option_score != float('-inf'):
                max_score += max_option_score
        
        return min_score, max_score
    
    def parse_csv_results(self, csv_content):
        """CSV 결과 데이터 파싱"""
        results_data = []
        
        try:
            lines = csv_content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
            lines = [line for line in lines if line.strip()]
            
            csv_reader = csv.reader(lines)
            rows = list(csv_reader)
            
            if len(rows) < 4:
                raise ValueError("CSV 파일에 충분한 데이터가 없습니다.")
            
            result_nums = rows[0][1:]
            
            for i, result_num in enumerate(result_nums):
                col_idx = i + 1
                
                result_data = {
                    'result_num': result_num,
                    'title': rows[1][col_idx] if len(rows[1]) > col_idx else f"결과 {result_num}",
                    'description': "",
                    'background_color': '#FFFFFF'
                }
                
                if len(rows) > 2 and len(rows[2]) > col_idx:
                    try:
                        result_data['min_score'] = int(rows[2][col_idx])
                    except (ValueError, TypeError):
                        result_data['min_score'] = 0
                
                if len(rows) > 3 and len(rows[3]) > col_idx:
                    try:
                        result_data['max_score'] = int(rows[3][col_idx])
                    except (ValueError, TypeError):
                        result_data['max_score'] = 100
                
                results_data.append(result_data)
            
            return results_data
            
        except Exception as e:
            print(f"CSV 파싱 오류: {str(e)}")
            raise
    
    def post(self, request, *args, **kwargs):
        csv_file = request.FILES.get('csv_file')
        csv_content = request.POST.get('csv_content')
        
        results_data = []
        result_images = {}
        result_sub_images = {}
        
        if csv_file or csv_content:
            if csv_content:
                try:
                    if csv_file:
                        path = f'temp/wizard/{request.session.session_key}/results.csv'
                        if default_storage.exists(path):
                            default_storage.delete(path)
                        path = default_storage.save(path, ContentFile(csv_file.read()))
                        request.session['wizard_results_csv_path'] = path
                    
                    csv_results = self.parse_csv_results(csv_content)
                    
                    if not csv_results:
                        messages.error(request, "CSV 파일에서 결과 데이터를 읽을 수 없습니다.")
                        return self.render_to_response(self.get_context_data())
                    
                    results_data = csv_results
                    
                except Exception as e:
                    messages.error(request, f"CSV 파일 처리 중 오류가 발생했습니다: {str(e)}")
                    return self.render_to_response(self.get_context_data())
            
            # CSV 결과 이미지 처리
            for key, file in request.FILES.items():
                if key.startswith('csv_results[') and key.endswith('][image]'):
                    index_str = key.split('[')[1].split(']')[0]
                    
                    try:
                        index = int(index_str)
                        path = f'temp/wizard/{request.session.session_key}/csv_result_{index}_image{os.path.splitext(file.name)[1]}'
                        if default_storage.exists(path):
                            default_storage.delete(path)
                        path = default_storage.save(path, ContentFile(file.read()))
                        
                        if 'wizard_csv_result_images' not in request.session:
                            request.session['wizard_csv_result_images'] = {}
                        
                        request.session['wizard_csv_result_images'][index_str] = path
                        request.session.modified = True
                    except (ValueError, IndexError):
                        continue
                
                elif key.startswith('csv_results[') and key.endswith('][sub_image]'):
                    index_str = key.split('[')[1].split(']')[0]
                    
                    try:
                        index = int(index_str)
                        path = f'temp/wizard/{request.session.session_key}/csv_result_{index}_sub_image{os.path.splitext(file.name)[1]}'
                        if default_storage.exists(path):
                            default_storage.delete(path)
                        path = default_storage.save(path, ContentFile(file.read()))
                        
                        if 'wizard_csv_result_sub_images' not in request.session:
                            request.session['wizard_csv_result_sub_images'] = {}
                        
                        request.session['wizard_csv_result_sub_images'][index_str] = path
                        request.session.modified = True
                    except (ValueError, IndexError):
                        continue
            
            # 배경 색상 처리
            for key, value in request.POST.items():
                if key.startswith('csv_results[') and key.endswith('][background_color]'):
                    index_str = key.split('[')[1].split(']')[0]
                    
                    try:
                        index = int(index_str)
                        
                        for result in results_data:
                            if result.get('result_num') == index_str:
                                result['background_color'] = value
                                break
                    except (ValueError, IndexError):
                        continue
        else:
            # 수동 입력 모드 처리
            for key, value in request.POST.items():
                if key.startswith('results[') and key.endswith('][title]'):
                    index_str = key.split('[')[1].split(']')[0]
                    index = int(index_str)
                    
                    if len(results_data) <= index:
                        while len(results_data) <= index:
                            results_data.append({})
                    
                    results_data[index]['title'] = value
            
            for key, value in request.POST.items():
                if key.startswith('results['):
                    parts = key.split('[')
                    index_str = parts[1].split(']')[0]
                    field = parts[2].split(']')[0]
                    index = int(index_str)
                    
                    if len(results_data) <= index:
                        continue
                    
                    if field in ['description', 'min_score', 'max_score', 'background_color']:
                        results_data[index][field] = value
            
            # 결과 이미지 처리
            for key, file in request.FILES.items():
                if key.startswith('results[') and key.endswith('][image]'):
                    index_str = key.split('[')[1].split(']')[0]
                    index = int(index_str)
                    
                    path = f'temp/wizard/{request.session.session_key}/result_{index}_image{os.path.splitext(file.name)[1]}'
                    if default_storage.exists(path):
                        default_storage.delete(path)
                    path = default_storage.save(path, ContentFile(file.read()))
                    result_images[index] = path
                
                elif key.startswith('results[') and key.endswith('][sub_image]'):
                    index_str = key.split('[')[1].split(']')[0]
                    index = int(index_str)
                    
                    path = f'temp/wizard/{request.session.session_key}/result_{index}_sub_image{os.path.splitext(file.name)[1]}'
                    if default_storage.exists(path):
                        default_storage.delete(path)
                    path = default_storage.save(path, ContentFile(file.read()))
                    result_sub_images[index] = path
            
            request.session['wizard_result_images'] = result_images
            request.session['wizard_result_sub_images'] = result_sub_images
        
        request.session['wizard_results_data'] = results_data
        print(f"저장된 결과 데이터: {results_data}")
        print(f"세션에 저장된 결과 데이터: {request.session.get('wizard_results_data')}")
        request.session.modified = True
        
        return redirect('admin:psychotest_test_wizard_sum_confirm')

@method_decorator(staff_member_required, name='dispatch')
class TestWizardSumConfirmView(TemplateView):
    """점수 합산 방식 테스트 마법사 최종 확인"""
    template_name = 'admin/psychotest/test/wizard_confirm_form.html'
    
    def get(self, request, *args, **kwargs):
        required_keys = ['wizard_test_info', 'wizard_questions_data']
        for key in required_keys:
            if key not in request.session:
                messages.warning(request, "테스트 정보가 불완전합니다. 처음부터 다시 시작해주세요.")
                return redirect('admin:psychotest_test_wizard_selection')
        
        test_info = request.session['wizard_test_info']
        questions_data = request.session['wizard_questions_data']
        results_data = request.session.get('wizard_results_data', [])
        
        calculation_method_display = {
            'sum': '점수 합산',
            'category': '카테고리 점수',
            'pattern': '패턴 매칭'
        }
        
        view_style_display = {
            'all': '모든 질문 한번에',
            'one': '한 질문씩'
        }
        
        test_info['calculation_method_display'] = calculation_method_display.get(test_info['calculation_method'], '')
        test_info['view_style_display'] = view_style_display.get(test_info['view_style'], '')
        
        category_name = '없음'
        if test_info.get('category_id'):
            try:
                category = Category.objects.get(id=test_info['category_id'])
                category_name = category.name
            except Category.DoesNotExist:
                pass
        
        test_image_url = None
        if 'wizard_test_image_path' in request.session:
            test_image_url = default_storage.url(request.session['wizard_test_image_path'])
        
        intro_image_url = None
        if 'wizard_intro_image_path' in request.session:
            intro_image_url = default_storage.url(request.session['wizard_intro_image_path'])
        
        question_images = request.session.get('wizard_question_images', {})
        for i, question in enumerate(questions_data):
            if str(i+1) in question_images:
                question['image_url'] = default_storage.url(question_images[str(i+1)])
        
        is_csv_mode = 'wizard_csv_result_images' in request.session
        
        if is_csv_mode:
            csv_result_images = request.session.get('wizard_csv_result_images', {})
            csv_result_sub_images = request.session.get('wizard_csv_result_sub_images', {})
            
            for result in results_data:
                result_num = result.get('result_num')
                if result_num and result_num in csv_result_images:
                    result['image_url'] = default_storage.url(csv_result_images[result_num])
                
                if result_num and result_num in csv_result_sub_images:
                    result['sub_image_url'] = default_storage.url(csv_result_sub_images[result_num])
        else:
            result_images = request.session.get('wizard_result_images', {})
            result_sub_images = request.session.get('wizard_result_sub_images', {})
            
            for i, result in enumerate(results_data):
                if i in result_images:
                    result['image_url'] = default_storage.url(result_images[i])
                
                if i in result_sub_images:
                    result['sub_image_url'] = default_storage.url(result_sub_images[i])
        
        context = self.get_context_data(**kwargs)
        context.update({
            'test_info': test_info,
            'category_name': category_name,
            'test_image_url': test_image_url,
            'intro_image_url': intro_image_url,
            'questions_data': questions_data,
            'results_data': results_data,
        })
        
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        """테스트 생성 처리"""
        try:
            with transaction.atomic():
                test = self.create_test(request)
                self.create_questions_options(request, test)
                self.create_results(request, test)
                self.cleanup_session_data(request)
                
                messages.success(request, "테스트가 성공적으로 생성되었습니다.")
                return redirect('admin:psychotest_test_change', object_id=test.id)
                
        except Exception as e:
            messages.error(request, f"테스트 생성 중 오류가 발생했습니다: {str(e)}")
            return self.render_to_response(self.get_context_data())
    
    def create_test(self, request):
        """테스트 생성"""
        test_info = request.session['wizard_test_info']
        
        category = None
        if test_info.get('category_id'):
            try:
                category = Category.objects.get(id=test_info['category_id'])
            except Category.DoesNotExist:
                pass
        
        test = Test.objects.create(
            title=test_info['title'],
            description=test_info['description'],
            category=category,
            calculation_method=test_info['calculation_method'],
            view_style=test_info['view_style']
        )
        
        if 'wizard_test_image_path' in request.session:
            with default_storage.open(request.session['wizard_test_image_path'], 'rb') as temp_file:
                file_content = ContentFile(temp_file.read())
                file_name = os.path.basename(request.session['wizard_test_image_path'])
                test.image.save(f'test_images/{file_name}', file_content)
        
        if 'wizard_intro_image_path' in request.session:
            with default_storage.open(request.session['wizard_intro_image_path'], 'rb') as temp_file:
                file_content = ContentFile(temp_file.read())
                file_name = os.path.basename(request.session['wizard_intro_image_path'])
                test.intro_image.save(f'test_intro_images/{file_name}', file_content)
        
        test.save()
        return test

    def create_questions_options(self, request, test):
        """질문 및 선택지 생성"""
        questions_data = request.session['wizard_questions_data']
        question_images = request.session.get('wizard_question_images', {})
        
        for i, question_data in enumerate(questions_data):
            question = Question.objects.create(
                test=test,
                text=question_data['text'],
                order=question_data.get('order', i+1)
            )
            
            if str(i+1) in question_images:
                with default_storage.open(question_images[str(i+1)], 'rb') as temp_file:
                    file_content = ContentFile(temp_file.read())
                    file_name = os.path.basename(question_images[str(i+1)])
                    question.image.save(f'question_images/{file_name}', file_content)
            
            for option_data in question_data['options']:
                Option.objects.create(
                    question=question,
                    text=option_data['text'],
                    score=option_data.get('score', 0),
                    category_scores={}
                )

    def create_results(self, request, test):
        """결과 생성"""
        is_csv_mode = 'wizard_csv_result_images' in request.session
        
        if is_csv_mode:
            results_data = request.session.get('wizard_results_data', [])
            csv_result_images = request.session.get('wizard_csv_result_images', {})
            csv_result_sub_images = request.session.get('wizard_csv_result_sub_images', {})
            
            for result_data in results_data:
                result = Result.objects.create(
                    test=test,
                    title=result_data['title'],
                    description=result_data.get('description', ''),
                    min_score=result_data.get('min_score', 0),
                    max_score=result_data.get('max_score', 100),
                    background_color=result_data.get('background_color', '#FFFFFF')
                )
                
                result_num = result_data.get('result_num')
                if result_num and result_num in csv_result_images:
                    with default_storage.open(csv_result_images[result_num], 'rb') as temp_file:
                        file_content = ContentFile(temp_file.read())
                        file_name = os.path.basename(csv_result_images[result_num])
                        result.image.save(f'result_images/{file_name}', file_content)
                
                if result_num and result_num in csv_result_sub_images:
                    with default_storage.open(csv_result_sub_images[result_num], 'rb') as temp_file:
                        file_content = ContentFile(temp_file.read())
                        file_name = os.path.basename(csv_result_sub_images[result_num])
                        result.sub_image.save(f'result_sub_images/{file_name}', file_content)
        else:
            results_data = request.session.get('wizard_results_data', [])
            result_images = request.session.get('wizard_result_images', {})
            result_sub_images = request.session.get('wizard_result_sub_images', {})
            
            for i, result_data in enumerate(results_data):
                result = Result.objects.create(
                    test=test,
                    title=result_data['title'],
                    description=result_data.get('description', ''),
                    min_score=int(result_data.get('min_score', 0)),
                    max_score=int(result_data.get('max_score', 100)),
                    background_color=result_data.get('background_color', '#FFFFFF')
                )
                
                if i in result_images:
                    with default_storage.open(result_images[i], 'rb') as temp_file:
                        file_content = ContentFile(temp_file.read())
                        file_name = os.path.basename(result_images[i])
                        result.image.save(f'result_images/{file_name}', file_content)
                
                if i in result_sub_images:
                    with default_storage.open(result_sub_images[i], 'rb') as temp_file:
                        file_content = ContentFile(temp_file.read())
                        file_name = os.path.basename(result_sub_images[i])
                        result.sub_image.save(f'result_sub_images/{file_name}', file_content)

    def cleanup_session_data(self, request):
        """세션 데이터 정리"""
        keys_to_remove = [
            'wizard_test_info',
            'wizard_test_image_path',
            'wizard_intro_image_path',
            'wizard_questions_data',
            'wizard_question_images',
            'wizard_results_data',
            'wizard_result_images',
            'wizard_result_sub_images',
            'wizard_csv_path',
            'wizard_results_csv_path',
            'wizard_csv_result_images',
            'wizard_csv_result_sub_images'
        ]
        
        for key in keys_to_remove:
            if key in request.session:
                del request.session[key]
        
        temp_dir = f'temp/wizard/{request.session.session_key}'
        if default_storage.exists(temp_dir):
            files = default_storage.listdir(temp_dir)[1]
            for file in files:
                file_path = os.path.join(temp_dir, file)
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)
            
            try:
                default_storage.delete(temp_dir)
            except:
                pass
        
        request.session.modified = True