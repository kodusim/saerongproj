from django import forms
from django.forms import inlineformset_factory
from .models import Test, Question, Option, Result, Category
from .widgets import CategoryScoreWidget

class OptionForm(forms.ModelForm):
    """선택지 폼"""
    
    class Meta:
        model = Option
        fields = ['text', 'score', 'category_scores']
        widgets = {
            'category_scores': CategoryScoreWidget(),
            'text': forms.TextInput(attrs={'class': 'vTextField', 'placeholder': '선택지 텍스트'}),
            'score': forms.NumberInput(attrs={'class': 'vIntegerField', 'min': -10, 'max': 10})
        }
        
class QuestionForm(forms.ModelForm):
    """질문 폼"""
    
    class Meta:
        model = Question
        fields = ['text', 'order']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'vTextField', 'placeholder': '질문 내용'}),
            'order': forms.NumberInput(attrs={'class': 'vIntegerField', 'min': 0})
        }
        
class ResultForm(forms.ModelForm):
    """결과 폼"""
    
    class Meta:
        model = Result
        fields = ['title', 'description', 'min_score', 'max_score', 'category', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'vTextField', 'placeholder': '결과 제목'}),
            'description': forms.Textarea(attrs={'class': 'vLargeTextField', 'rows': 4}),
        }
        
    def __init__(self, *args, **kwargs):
        super(ResultForm, self).__init__(*args, **kwargs)
        # 테스트의 계산 방식에 따라 필드 표시 여부 조정
        instance = kwargs.get('instance')
        if instance:
            test = instance.test
            if test.calculation_method == 'category':
                self.fields['min_score'].widget = forms.HiddenInput()
                self.fields['max_score'].widget = forms.HiddenInput()
            elif test.calculation_method == 'sum':
                self.fields['category'].widget = forms.HiddenInput()
                
# 인라인 폼셋 정의
OptionFormSet = inlineformset_factory(
    Question, 
    Option, 
    form=OptionForm, 
    extra=2,  # 기본으로 표시할 빈 폼 수
    can_delete=True
)

QuestionFormSet = inlineformset_factory(
    Test, 
    Question, 
    form=QuestionForm, 
    extra=1,
    can_delete=True
)

ResultFormSet = inlineformset_factory(
    Test, 
    Result, 
    form=ResultForm, 
    extra=1,
    can_delete=True
)