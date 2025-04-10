from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django import forms
from django.template.response import TemplateResponse

from .models import Category, Test, Question, Option, Result
from .forms import OptionForm, QuestionForm, ResultForm
from .utils.import_handler import TestImportHandler
from .utils.test_wizard import TestWizardHandler

class TestImportForm(forms.Form):
    """테스트 일괄 등록을 위한 폼"""
    file = forms.FileField(label='Excel 파일 업로드', 
                           help_text='테스트, 질문, 선택지, 결과가 포함된 Excel 파일을 업로드하세요.')

class OptionInline(admin.TabularInline):
    model = Option
    form = OptionForm
    extra = 2
    fieldsets = (
        (None, {
            'fields': ('text', 'score')
        }),
        ('카테고리별 점수 (고급)', {
            'classes': ('collapse',),
            'fields': ('category_scores',),
        }),
    )

class QuestionInline(admin.StackedInline):
    model = Question
    form = QuestionForm
    extra = 1
    show_change_link = True
    fields = ('text', 'order')

class ResultInline(admin.StackedInline):
    model = Result
    form = ResultForm
    extra = 1
    fields = ('title', 'description', 'min_score', 'max_score', 'category', 'image')

    def get_fieldsets(self, request, obj=None):
        """테스트 계산 방식에 따라 필드 변경"""
        if obj and obj.test and obj.test.calculation_method == 'category':
            return (
                (None, {
                    'fields': ('title', 'description', 'category', 'image')
                }),
            )
        elif obj and obj.test and obj.test.calculation_method == 'sum':
            return (
                (None, {
                    'fields': ('title', 'description', 'min_score', 'max_score', 'image')
                }),
            )
        else:
            return super().get_fieldsets(request, obj)

class TestAdmin(admin.ModelAdmin):
    inlines = [QuestionInline, ResultInline]
    list_display = ['title', 'category', 'created_at', 'calculation_method', 'view_style', 'view_count', 'show_thumbnail', 'questions_count', 'results_count']
    list_filter = ['category', 'calculation_method', 'view_style']
    search_fields = ['title', 'description']
    readonly_fields = ['image_preview', 'intro_image_preview']
    actions = ['copy_test']
    
    def show_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No Image"
    show_thumbnail.short_description = '썸네일'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" />', obj.image.url)
        return "No Image"
    image_preview.short_description = '썸네일 미리보기'
    
    def intro_image_preview(self, obj):
        if obj.intro_image:
            return format_html('<img src="{}" width="300" />', obj.intro_image.url)
        return "No Image"
    intro_image_preview.short_description = '인트로 이미지 미리보기'
    
    def questions_count(self, obj):
        return obj.questions.count()
    questions_count.short_description = '질문 수'
    
    def results_count(self, obj):
        return obj.results.count()
    results_count.short_description = '결과 수'
    
    def copy_test(self, request, queryset):
        """테스트 복사 액션"""
        for test in queryset:
            # 새 테스트 생성
            new_test = Test.objects.create(
                title=f'{test.title} (복사본)',
                description=test.description,
                category=test.category,
                calculation_method=test.calculation_method,
                view_style=test.view_style,
                image=test.image,
                intro_image=test.intro_image
            )
            
            # 질문 복사
            for question in test.questions.all():
                new_question = Question.objects.create(
                    test=new_test,
                    text=question.text,
                    order=question.order
                )
                
                # 선택지 복사
                for option in question.options.all():
                    Option.objects.create(
                        question=new_question,
                        text=option.text,
                        score=option.score,
                        category_scores=option.category_scores
                    )
            
            # 결과 복사
            for result in test.results.all():
                new_result = Result.objects.create(
                    test=new_test,
                    title=result.title,
                    description=result.description,
                    min_score=result.min_score,
                    max_score=result.max_score,
                    category=result.category,
                    image=result.image
                )
        
        messages.success(request, f"{queryset.count()}개의 테스트가 복사되었습니다.")
    copy_test.short_description = "선택한 테스트 복사하기"
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'category', 'calculation_method', 'view_style')
        }),
        ('이미지', {
            'fields': ('image', 'image_preview', 'intro_image', 'intro_image_preview'),
        }),
        ('통계', {
            'fields': ('view_count',),
        }),
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-test/', 
                 self.admin_site.admin_view(self.import_test_view), 
                 name='psychotest_test_import'),
            path('add-test-wizard/', 
                 self.admin_site.admin_view(self.add_test_wizard_view), 
                 name='psychotest_test_wizard'),
            path('<int:test_id>/questions/',
                 self.admin_site.admin_view(self.questions_view),
                 name='psychotest_test_questions'),
            path('<int:test_id>/results/',
                 self.admin_site.admin_view(self.results_view),
                 name='psychotest_test_results'),
        ]
        return custom_urls + urls
    
    def import_test_view(self, request):
        """Excel 파일을 통한 테스트 일괄 등록 뷰"""
        if request.method == 'POST':
            form = TestImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = request.FILES['file']
                import_handler = TestImportHandler(file)
                
                success = import_handler.import_tests()
                if success:
                    self.message_user(request, "테스트 일괄 등록이 완료되었습니다.")
                    return redirect('admin:psychotest_test_changelist')
                else:
                    for error in import_handler.errors:
                        messages.error(request, error)
        else:
            form = TestImportForm()
        
        context = {
            'form': form,
            'title': '테스트 일괄 등록',
            'opts': self.model._meta,
            'add': True,
            'is_popup': False,
            'save_as': False,
            'has_delete_permission': False,
            'has_add_permission': True,
            'has_change_permission': True,
        }
        return render(request, 'admin/psychotest/test/import_form.html', context)
    
    def add_test_wizard_view(self, request):
        """테스트 추가 마법사 뷰"""
        if request.method == 'POST':
            wizard_handler = TestWizardHandler(request)
            
            try:
                test = wizard_handler.create_test()
                if test:
                    return JsonResponse({
                        'success': True,
                        'redirect_url': f'/admin/psychotest/test/{test.id}/change/'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': "테스트 생성에 실패했습니다: " + " ".join(wizard_handler.errors)
                    })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f"오류가 발생했습니다: {str(e)}"
                })
        
        # 카테고리 목록 가져오기
        categories = Category.objects.all()
        
        context = {
            'title': '테스트 추가 마법사',
            'opts': self.model._meta,
            'add': True,
            'is_popup': False,
            'categories': categories,
            'has_delete_permission': False,
            'has_add_permission': True,
            'has_change_permission': True,
        }
        return render(request, 'admin/psychotest/test/wizard_form.html', context)
    
    def questions_view(self, request, test_id):
        """선택한 테스트의 질문 관리 뷰"""
        test = get_object_or_404(Test, id=test_id)
        categories = Category.objects.all()
        
        if request.method == 'POST':
            # 기존 질문 업데이트
            self._process_existing_questions(request, test)
            
            # 새 질문 추가
            self._process_new_questions(request, test)
            
            # 선택지 삭제 처리
            self._process_option_deletion(request)
            
            messages.success(request, "질문과 선택지가 성공적으로 저장되었습니다.")
            return redirect('admin:psychotest_test_change', object_id=test_id)
        
        # 질문 폼 데이터 준비
        from django.forms import modelformset_factory
        QuestionFormSet = modelformset_factory(Question, form=QuestionForm, extra=1, can_delete=True)
        formset = QuestionFormSet(queryset=Question.objects.filter(test=test).order_by('order'))
        
        context = {
            'test': test,
            'formset': formset,
            'categories': categories,
            'title': f'{test.title} - 질문 관리',
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
            'has_delete_permission': False,
            'has_add_permission': True,
            'has_change_permission': True,
        }
        return TemplateResponse(request, 'admin/psychotest/test/questions_form.html', context)
    
    def results_view(self, request, test_id):
        """선택한 테스트의 결과 관리 뷰"""
        test = get_object_or_404(Test, id=test_id)
        categories = Category.objects.all()
        
        if request.method == 'POST':
            from django.forms import modelformset_factory
            ResultFormSet = modelformset_factory(Result, form=ResultForm, extra=1, can_delete=True)
            formset = ResultFormSet(request.POST, request.FILES, queryset=Result.objects.filter(test=test))
            
            if formset.is_valid():
                results = formset.save(commit=False)
                for result in results:
                    result.test = test
                    result.save()
                
                # 삭제 처리
                for obj in formset.deleted_objects:
                    obj.delete()
                
                messages.success(request, "결과가 성공적으로 저장되었습니다.")
                return redirect('admin:psychotest_test_change', object_id=test_id)
            else:
                messages.error(request, "폼 유효성 검사에 실패했습니다.")
        else:
            from django.forms import modelformset_factory
            ResultFormSet = modelformset_factory(Result, form=ResultForm, extra=1, can_delete=True)
            formset = ResultFormSet(queryset=Result.objects.filter(test=test))
        
        context = {
            'test': test,
            'formset': formset,
            'categories': categories,
            'title': f'{test.title} - 결과 관리',
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
            'has_delete_permission': False,
            'has_add_permission': True,
            'has_change_permission': True,
        }
        return TemplateResponse(request, 'admin/psychotest/test/results_form.html', context)
    
    def _process_existing_questions(self, request, test):
        """기존 질문 처리"""
        from django.forms import modelformset_factory
        QuestionFormSet = modelformset_factory(Question, form=QuestionForm, can_delete=True)
        formset = QuestionFormSet(request.POST, queryset=Question.objects.filter(test=test))
        
        if formset.is_valid():
            # 질문 저장
            questions = formset.save(commit=False)
            for question in questions:
                question.test = test
                question.save()
            
            # 삭제 처리
            for obj in formset.deleted_objects:
                obj.delete()
            
            # 기존 선택지 업데이트
            for question in test.questions.all():
                # 각 질문의 선택지 업데이트
                for option in question.options.all():
                    option_text_key = f'option_{option.id}_text'
                    option_score_key = f'option_{option.id}_score'
                    
                    if option_text_key in request.POST:
                        option.text = request.POST[option_text_key]
                        option.score = int(request.POST.get(option_score_key, 0))
                        
                        # 카테고리 점수 처리 (카테고리 계산 방식인 경우)
                        if test.calculation_method == 'category':
                            category_scores = {}
                            for category in Category.objects.all():
                                score_key = f'option_{option.id}_category_{category.id}'
                                if score_key in request.POST and request.POST[score_key]:
                                    score = int(request.POST[score_key])
                                    if score != 0:
                                        category_scores[category.name] = score
                            
                            option.category_scores = category_scores
                        
                        option.save()
    
    def _process_new_questions(self, request, test):
        """새 질문 추가 처리"""
        # 새 질문 필드 탐색
        for key, value in request.POST.items():
            if key.startswith('new_question_') and key.endswith('_text') and value:
                # 새 질문 ID 추출
                question_id = key.replace('new_question_', '').replace('_text', '')
                
                # 질문 순서 가져오기
                order_key = f'new_question_{question_id}_order'
                order = int(request.POST.get(order_key, 0))
                
                # 새 질문 생성
                question = Question.objects.create(
                    test=test,
                    text=value,
                    order=order
                )
                
                # 해당 질문의 새 선택지 처리
                self._process_new_options(request, question, question_id)
    
    def _process_new_options(self, request, question, question_id):
        """새 선택지 추가 처리"""
        option_index = 0
        
        while True:
            text_key = f'new_option_{question_id}_{option_index}_text'
            if text_key not in request.POST or not request.POST[text_key]:
                break
            
            score_key = f'new_option_{question_id}_{option_index}_score'
            score = int(request.POST.get(score_key, 0))
            
            # 카테고리 점수 처리
            category_scores = {}
            if question.test.calculation_method == 'category':
                for category in Category.objects.all():
                    category_key = f'new_option_{question_id}_{option_index}_category_{category.id}'
                    if category_key in request.POST and request.POST[category_key]:
                        category_score = int(request.POST[category_key])
                        if category_score != 0:
                            category_scores[category.name] = category_score
            
            # 새 선택지 생성
            Option.objects.create(
                question=question,
                text=request.POST[text_key],
                score=score,
                category_scores=category_scores
            )
            
            option_index += 1
    
    def _process_option_deletion(self, request):
        """선택지 삭제 처리"""
        for key, value in request.POST.items():
            if key.startswith('delete_option_') and value == 'true':
                option_id = key.replace('delete_option_', '')
                try:
                    option = Option.objects.get(id=option_id)
                    option.delete()
                except Option.DoesNotExist:
                    pass
                
    def changelist_view(self, request, extra_context=None):
        """목록 뷰에 추가 버튼 표시"""
        extra_context = extra_context or {}
        extra_context['show_wizard_button'] = True
        extra_context['show_import_button'] = True
        return super().changelist_view(request, extra_context)
    

class QuestionAdmin(admin.ModelAdmin):
    inlines = [OptionInline]
    list_display = ['text', 'test', 'order', 'options_count']
    list_filter = ['test']
    search_fields = ['text']
    
    def options_count(self, obj):
        return obj.options.count()
    options_count.short_description = '선택지 수'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('test')
    
class OptionAdmin(admin.ModelAdmin):
    list_display = ['text', 'question', 'score', 'question_test']
    list_filter = ['question__test']
    search_fields = ['text']
    form = OptionForm
    
    def question_test(self, obj):
        return obj.question.test
    question_test.short_description = '테스트'
    question_test.admin_order_field = 'question__test'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('question', 'question__test')
    
    fieldsets = (
        (None, {
            'fields': ('question', 'text', 'score')
        }),
        ('카테고리별 점수 (고급)', {
            'classes': ('collapse',),
            'fields': ('category_scores',),
        }),
    )

class ResultAdmin(admin.ModelAdmin):
    list_display = ['title', 'test', 'min_score', 'max_score', 'category']
    list_filter = ['test']
    search_fields = ['title', 'description']
    form = ResultForm
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('test')
    
    def get_fieldsets(self, request, obj=None):
        """테스트 계산 방식에 따라 필드 변경"""
        if obj and obj.test and obj.test.calculation_method == 'category':
            return (
                (None, {
                    'fields': ('test', 'title', 'description', 'category', 'image')
                }),
            )
        elif obj and obj.test and obj.test.calculation_method == 'sum':
            return (
                (None, {
                    'fields': ('test', 'title', 'description', 'min_score', 'max_score', 'image')
                }),
            )
        else:
            return (
                (None, {
                    'fields': ('test', 'title', 'description')
                }),
                ('점수 범위 (점수 합산 방식)', {
                    'fields': ('min_score', 'max_score'),
                }),
                ('카테고리 (카테고리 점수 방식)', {
                    'fields': ('category',),
                }),
                ('이미지', {
                    'fields': ('image',),
                }),
            )

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'tests_count']
    search_fields = ['name', 'description']
    
    def tests_count(self, obj):
        return obj.tests.count()
    tests_count.short_description = '테스트 수'

# 관리자 페이지에 등록
admin.site.register(Category, CategoryAdmin)
admin.site.register(Test, TestAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Option, OptionAdmin)
admin.site.register(Result, ResultAdmin)