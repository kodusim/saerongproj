from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django import forms
from .models import Category, Test, Question, Option, Result, SharedTestResult
from .forms import OptionForm, QuestionForm, ResultForm
from .admin_views import (
    TestWizardMethodSelectionView, 
    TestWizardSumView, 
    TestWizardSumQuestionsView,
    TestWizardSumResultsView, 
    TestWizardSumConfirmView
)

class OptionInline(admin.TabularInline):
    model = Option
    form = OptionForm
    extra = 0 
    fields = ('text', 'score')

class QuestionInline(admin.StackedInline):
    model = Question
    form = QuestionForm
    extra = 1
    show_change_link = True
    fields = ('text', 'order')
    inlines = [OptionInline]

class ResultInline(admin.StackedInline):
    model = Result
    form = ResultForm
    extra = 1
    fields = ('title', 'description', 'min_score', 'max_score', 'category', 'image', 'sub_image', 'background_color')

    def get_fieldsets(self, request, obj=None):
        """테스트 계산 방식에 따라 필드 변경"""
        test_obj = None
        
        if obj:  # obj는 Test 객체입니다
            test_obj = obj
        
        if test_obj and test_obj.calculation_method == 'category':
            return (
                (None, {
                    'fields': ('title', 'description', 'category', 'image', 'sub_image', 'background_color')
                }),
            )
        elif test_obj and test_obj.calculation_method == 'sum':
            return (
                (None, {
                    'fields': ('title', 'description', 'min_score', 'max_score', 'image', 'sub_image', 'background_color')
                }),
            )
        else:
            return super().get_fieldsets(request, obj)

class TestAdmin(admin.ModelAdmin):
    inlines = [QuestionInline, ResultInline]
    list_display = ['title', 'category', 'created_at', 'calculation_method', 'view_style', 'view_count', 'show_thumbnail', 'questions_count', 'results_count']
    list_filter = ['category', 'calculation_method', 'view_style']
    search_fields = ['title', 'description']
    readonly_fields = ['image_preview', 'intro_image_preview', 'gauge_character_preview']
    actions = ['copy_test']

    def gauge_character_preview(self, obj):
        if obj.gauge_character:
            return format_html('<img src="{}" width="30" height="30" />', obj.gauge_character.url)
        return "No Image"
    gauge_character_preview.short_description = '게이지 캐릭터 미리보기'

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
            'fields': ('image', 'image_preview', 'intro_image', 'intro_image_preview', 
                      'gauge_character', 'gauge_character_preview'),
        }),
        ('통계', {
            'fields': ('view_count',),
        }),
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # 새로운 마법사 메서드 선택 뷰
            path('wizard-selection/', 
                self.admin_site.admin_view(TestWizardMethodSelectionView.as_view()), 
                name='psychotest_test_wizard_selection'),
            # 점수 합산 방식 마법사 - 테스트 정보 입력
            path('wizard-sum/', 
                self.admin_site.admin_view(TestWizardSumView.as_view()), 
                name='psychotest_test_wizard_sum'),
            # 점수 합산 방식 마법사 - 질문지 입력
            path('wizard-sum/questions/', 
                self.admin_site.admin_view(TestWizardSumQuestionsView.as_view()), 
                name='psychotest_test_wizard_sum_questions'),
            # 점수 합산 방식 마법사 - 결과 설정
            path('wizard-sum/results/', 
                self.admin_site.admin_view(TestWizardSumResultsView.as_view()), 
                name='psychotest_test_wizard_sum_results'),
            # 점수 합산 방식 마법사 - 최종 확인
            path('wizard-sum/confirm/', 
                self.admin_site.admin_view(TestWizardSumConfirmView.as_view()), 
                name='psychotest_test_wizard_sum_confirm'),
        ]
        return custom_urls + urls
    
    def changelist_view(self, request, extra_context=None):
        """목록 뷰에 추가 버튼 표시"""
        extra_context = extra_context or {}
        extra_context['show_wizard_button'] = True
        
        # 템플릿에서 새 마법사 URL을 사용할 수 있게 URL 추가
        from django.urls import reverse
        extra_context['new_wizard_url'] = reverse('admin:psychotest_test_wizard_selection')
        return super().changelist_view(request, extra_context)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'tests_count']
    search_fields = ['name', 'description']
    
    def tests_count(self, obj):
        return obj.tests.count()
    tests_count.short_description = '테스트 수'

class SharedTestResultAdmin(admin.ModelAdmin):
    """공유된 테스트 결과 관리자"""
    list_display = ['id', 'test', 'result', 'calculation_method', 'created_at']
    list_filter = ['test', 'calculation_method', 'created_at']
    search_fields = ['test__title', 'result__title']
    readonly_fields = ['id', 'created_at']
    fieldsets = (
        (None, {
            'fields': ('id', 'test', 'result')
        }),
        ('결과 정보', {
            'fields': ('calculation_method', 'score', 'category', 'category_scores')
        }),
        ('메타데이터', {
            'fields': ('created_at',)
        }),
    )
    
    def has_add_permission(self, request):
        """공유된 결과는 시스템에 의해 자동 생성되므로 관리자에서 직접 추가하지 않음"""
        return False
class QuestionAdmin(admin.ModelAdmin):
    inlines = [OptionInline]
    list_display = ['text', 'test', 'order']
    list_filter = ['test']
    search_fields = ['text']

class OptionAdmin(admin.ModelAdmin):
    list_display = ['text', 'question', 'score']
    list_filter = ['question__test']
    search_fields = ['text']

admin.site.register(Option, OptionAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Test, TestAdmin)
admin.site.register(SharedTestResult, SharedTestResultAdmin)