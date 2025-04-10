import json
import pandas as pd
from django.db import transaction
from ..models import Test, Question, Option, Result, Category

class TestImportHandler:
    """Excel 파일을 사용하여 테스트를 일괄 가져오는 핸들러"""
    
    def __init__(self, file):
        self.file = file
        self.errors = []
    
    def import_tests(self):
        """테스트 일괄 가져오기 실행"""
        try:
            # Excel 파일 읽기
            excel_data = pd.ExcelFile(self.file)
            
            # 필수 시트 확인
            required_sheets = ['테스트', '질문', '선택지', '결과']
            for sheet in required_sheets:
                if sheet not in excel_data.sheet_names:
                    self.errors.append(f"필수 시트 '{sheet}'가 Excel 파일에 없습니다.")
                    return False
            
            # 각 시트 데이터 읽기
            tests_df = pd.read_excel(excel_data, '테스트')
            questions_df = pd.read_excel(excel_data, '질문')
            options_df = pd.read_excel(excel_data, '선택지')
            results_df = pd.read_excel(excel_data, '결과')
            
            # 기본 유효성 검사
            if tests_df.empty:
                self.errors.append("테스트 시트에 데이터가 없습니다.")
                return False
            
            # 트랜잭션으로 데이터베이스 일괄 처리
            with transaction.atomic():
                imported_tests = self._import_tests(tests_df)
                self._import_questions(questions_df, imported_tests)
                self._import_options(options_df, imported_tests)
                self._import_results(results_df, imported_tests)
            
            return True
            
        except Exception as e:
            self.errors.append(f"가져오기 오류: {str(e)}")
            return False
    
    def _import_tests(self, tests_df):
        """테스트 데이터 가져오기"""
        imported_tests = {}
        
        for _, row in tests_df.iterrows():
            title = row.get('제목')
            description = row.get('설명')
            
            if not title or not description:
                self.errors.append("테스트 시트에 필수 필드(제목, 설명)가 누락되었습니다.")
                continue
            
            category_id = row.get('카테고리ID')
            calculation_method = row.get('계산방식', 'sum')
            view_style = row.get('보기방식', 'all')
            
            # 계산 방식 및 보기 방식 유효성 검사
            if calculation_method not in ['sum', 'category', 'pattern']:
                calculation_method = 'sum'
            
            if view_style not in ['all', 'one']:
                view_style = 'all'
            
            # 카테고리 참조 (있는 경우)
            category = None
            if category_id and not pd.isna(category_id):
                try:
                    category = Category.objects.get(id=int(category_id))
                except Category.DoesNotExist:
                    pass
            
            # 테스트 생성
            test = Test.objects.create(
                title=title,
                description=description,
                category=category,
                calculation_method=calculation_method,
                view_style=view_style
            )
            
            # 생성된 테스트 기록 (Excel 행 번호 → 테스트 ID)
            imported_tests[len(imported_tests) + 1] = test
        
        return imported_tests
    
    def _import_questions(self, questions_df, imported_tests):
        """질문 데이터 가져오기"""
        if questions_df.empty:
            self.errors.append("질문 시트에 데이터가 없습니다.")
            return
        
        imported_questions = {}
        
        for _, row in questions_df.iterrows():
            test_id = row.get('테스트ID')
            text = row.get('질문텍스트')
            
            if not test_id or not text or pd.isna(test_id) or pd.isna(text):
                self.errors.append("질문 시트에 필수 필드(테스트ID, 질문텍스트)가 누락되었습니다.")
                continue
            
            # 해당 테스트 찾기
            test = imported_tests.get(int(test_id))
            if not test:
                self.errors.append(f"테스트ID {test_id}에 해당하는 테스트를 찾을 수 없습니다.")
                continue
            
            # 순서 확인
            order = row.get('순서')
            if pd.isna(order):
                # 해당 테스트의 마지막 질문 순서 + 1
                last_question = Question.objects.filter(test=test).order_by('-order').first()
                order = (last_question.order + 1) if last_question else 1
            else:
                order = int(order)
            
            # 질문 생성
            question = Question.objects.create(
                test=test,
                text=text,
                order=order
            )
            
            # 생성된 질문 기록 (Excel 행 번호 → 질문 ID)
            imported_questions[len(imported_questions) + 1] = question
        
        return imported_questions
    
    def _import_options(self, options_df, imported_tests):
        """선택지 데이터 가져오기"""
        if options_df.empty:
            self.errors.append("선택지 시트에 데이터가 없습니다.")
            return
        
        for _, row in options_df.iterrows():
            question_id = row.get('질문ID')
            text = row.get('선택지텍스트')
            
            if not question_id or not text or pd.isna(question_id) or pd.isna(text):
                self.errors.append("선택지 시트에 필수 필드(질문ID, 선택지텍스트)가 누락되었습니다.")
                continue
            
            # 질문 ID를 기반으로 실제 질문 찾기
            question_id = int(question_id)
            questions = Question.objects.filter(id=question_id)
            
            if not questions.exists():
                self.errors.append(f"질문ID {question_id}에 해당하는 질문을 찾을 수 없습니다.")
                continue
            
            question = questions.first()
            
            # 점수 확인
            score = row.get('점수', 0)
            if pd.isna(score):
                score = 0
            else:
                score = int(score)
            
            # 카테고리 점수 확인
            category_scores = row.get('카테고리점수')
            if not pd.isna(category_scores):
                try:
                    # JSON 형식 확인
                    if isinstance(category_scores, str):
                        category_scores = json.loads(category_scores.replace("'", '"'))
                except json.JSONDecodeError:
                    category_scores = {}
            else:
                category_scores = {}
            
            # 선택지 생성
            Option.objects.create(
                question=question,
                text=text,
                score=score,
                category_scores=category_scores
            )
    
    def _import_results(self, results_df, imported_tests):
        """결과 데이터 가져오기"""
        if results_df.empty:
            self.errors.append("결과 시트에 데이터가 없습니다.")
            return
        
        for _, row in results_df.iterrows():
            test_id = row.get('테스트ID')
            title = row.get('결과제목')
            description = row.get('결과설명')
            
            if not test_id or not title or not description or pd.isna(test_id) or pd.isna(title) or pd.isna(description):
                self.errors.append("결과 시트에 필수 필드(테스트ID, 결과제목, 결과설명)가 누락되었습니다.")
                continue
            
            # 해당 테스트 찾기
            test = imported_tests.get(int(test_id))
            if not test:
                self.errors.append(f"테스트ID {test_id}에 해당하는 테스트를 찾을 수 없습니다.")
                continue
            
            # 테스트 계산 방식에 따라 필요한 필드 확인
            if test.calculation_method == 'sum':
                min_score = row.get('최소점수')
                max_score = row.get('최대점수')
                
                if pd.isna(min_score) or pd.isna(max_score):
                    self.errors.append(f"점수 합산 방식 테스트의 결과에는 최소점수와 최대점수가 필요합니다.")
                    continue
                
                min_score = int(min_score)
                max_score = int(max_score)
                category = None
            
            elif test.calculation_method == 'category':
                category = row.get('카테고리')
                
                if pd.isna(category):
                    self.errors.append(f"카테고리 점수 방식 테스트의 결과에는 카테고리가 필요합니다.")
                    continue
                
                min_score = None
                max_score = None
            
            else:  # pattern
                min_score = None
                max_score = None
                category = None
            
            # 결과 생성
            Result.objects.create(
                test=test,
                title=title,
                description=description,
                min_score=min_score,
                max_score=max_score,
                category=category
            )