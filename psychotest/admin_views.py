from django.views.generic import TemplateView
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from .models import Category, Test

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
        # 카테고리 목록 가져오기
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
            # 파일 업로드 처리는 실제 구현 시 세션이 아닌 다른 방식으로 처리해야 함
            # 여기서는 파일 이름만 저장
            request.session['wizard_test_image'] = request.FILES['image'].name
        
        if 'intro_image' in request.FILES:
            request.session['wizard_intro_image'] = request.FILES['intro_image'].name
        
        # 다음 단계로 이동 - 아직 URL이 설정되지 않았으므로 임시로 관리자 페이지로 이동
        return redirect('admin:psychotest_test_changelist')  # 임시 리다이렉트
    
@method_decorator(staff_member_required, name='dispatch')
class TestWizardSumQuestionsView(TemplateView):
    """점수 합산 방식의 테스트 질문 입력 단계"""
    template_name = 'admin/psychotest/test/wizard_questions_form.html'
    
    def get(self, request, *args, **kwargs):
        # 이전 단계 정보가 없으면 첫 단계로 리다이렉트
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
        
        # CSV 데이터 세션에 저장
        if csv_content:
            request.session['wizard_questions_csv'] = csv_content
        
        # 다음 단계로 이동 - 결과 설정 페이지
        return redirect('admin:psychotest_test_wizard_sum_results')  # 다음 단계로 이동