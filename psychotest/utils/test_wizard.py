import json
from django.db import transaction
from ..models import Test, Question, Option, Result, Category

class TestWizardHandler:
    """테스트 마법사를 위한 핸들러"""
    
    def __init__(self, request):
        self.request = request
        self.errors = []
    
    @transaction.atomic
    def create_test(self):
        """폼 데이터에서 테스트 생성"""
        try:
            data = self.request.POST
            files = self.request.FILES
            
            # 1. 테스트 기본 정보 처리
            title = data.get('title')
            description = data.get('description')
            view_style = data.get('view_style', 'all')
            
            if not title or not description:
                self.errors.append("테스트 제목과 설명은 필수입니다.")
                return None
            
            # 카테고리 처리
            category = None
            category_id = data.get('category')
            if category_id:
                try:
                    category = Category.objects.get(id=category_id)
                except Category.DoesNotExist:
                    pass
            
            # 테스트 생성 - 계산 방식은 항상 'sum'으로 설정
            test = Test.objects.create(
                title=title,
                description=description,
                category=category,
                calculation_method='sum',  # 항상 'sum'으로 고정
                view_style=view_style
            )
            
            # 이미지 처리
            if 'image' in files:
                test.image = files['image']
            
            if 'intro_image' in files:
                test.intro_image = files['intro_image']
            
            test.save()
            
            # 2. 질문 및 선택지 처리
            self._process_questions(data, test)
            
            # 3. 결과 처리
            self._process_results(data, files, test)
            
            return test
                
        except Exception as e:
            self.errors.append(f"테스트 생성 오류: {str(e)}")
            raise
    
    def _process_questions(self, data, test):
        """질문 및 선택지 처리"""
        # 질문 데이터 구조화
        questions_data = {}
        
        for key in data.keys():
            # 질문 텍스트 필드 확인
            if key.startswith('questions[') and key.endswith('][text]'):
                # 질문 인덱스 추출
                q_index = key.split('[')[1].split(']')[0]
                
                if q_index not in questions_data:
                    questions_data[q_index] = {'options': {}}
                
                questions_data[q_index]['text'] = data[key]
            
            # 질문 순서 필드 확인
            elif key.startswith('questions[') and key.endswith('][order]'):
                q_index = key.split('[')[1].split(']')[0]
                
                if q_index not in questions_data:
                    questions_data[q_index] = {'options': {}}
                
                questions_data[q_index]['order'] = int(data[key])
            
            # 선택지 필드 확인
            elif key.startswith('questions[') and '[options][' in key:
                parts = key.split('[')
                q_index = parts[1].split(']')[0]
                o_index = parts[3].split(']')[0]
                field = parts[4].split(']')[0]
                
                if q_index not in questions_data:
                    questions_data[q_index] = {'options': {}}
                
                if o_index not in questions_data[q_index]['options']:
                    questions_data[q_index]['options'][o_index] = {}
                
                questions_data[q_index]['options'][o_index][field] = data[key]
        
        # 질문 생성
        for q_index, q_data in questions_data.items():
            if not q_data.get('text'):
                continue
            
            order = q_data.get('order', 0)
            
            question = Question.objects.create(
                test=test,
                text=q_data['text'],
                order=order
            )
            
            # 선택지 생성
            for o_index, o_data in q_data['options'].items():
                if not o_data.get('text'):
                    continue
                
                score = int(o_data.get('score', 0))
                
                # 선택지 생성 - category_scores는 항상 빈 딕셔너리로 설정
                Option.objects.create(
                    question=question,
                    text=o_data['text'],
                    score=score,
                    category_scores={}
                )
    
    def _process_results(self, data, files, test):
        """결과 처리"""
        # 결과 데이터 구조화
        results_data = {}
        
        for key in data.keys():
            if not key.startswith('results['):
                continue
            
            # 결과 인덱스 및 필드 추출
            parts = key.split('[')
            r_index = parts[1].split(']')[0]
            field = parts[2].split(']')[0]
            
            if r_index not in results_data:
                results_data[r_index] = {}
            
            results_data[r_index][field] = data[key]
        
        # 결과 생성
        for r_index, r_data in results_data.items():
            if not r_data.get('title') or not r_data.get('description'):
                continue
            
            # 점수 합산 방식에 필요한 필드만 사용
            min_score = int(r_data.get('min_score', 0))
            max_score = int(r_data.get('max_score', 100))
            
            # 결과 생성 - category 필드는 항상 None으로 설정
            result = Result.objects.create(
                test=test,
                title=r_data['title'],
                description=r_data['description'],
                min_score=min_score,
                max_score=max_score,
                category=None
            )
            
            # 이미지 처리
            image_key = f'results[{r_index}][image]'
            if image_key in files:
                result.image = files[image_key]
                result.save()