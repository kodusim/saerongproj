import json
from django.forms import Widget
from django.forms.widgets import Textarea
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from .models import Category

class CategoryScoreWidget(Widget):
    """카테고리별 점수를 입력하기 위한 커스텀 위젯"""
    template_name = 'admin/widgets/category_score_widget.html'
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        
        # 기본값 설정 - value가 None인 경우를 처리
        category_scores_dict = {}
        
        # JSON 형식의 값을 파싱
        if value:
            if isinstance(value, str):
                try:
                    category_scores_dict = json.loads(value)
                except json.JSONDecodeError:
                    category_scores_dict = {}
            elif isinstance(value, dict):
                category_scores_dict = value
            
        # 모든 카테고리 가져오기
        categories = Category.objects.all()
        category_scores = []
        
        for category in categories:
            score = 0
            if category_scores_dict and category.name in category_scores_dict:
                score = category_scores_dict[category.name]
                
            category_scores.append({
                'id': category.id,
                'name': category.name,
                'score': score
            })
        
        context['widget']['category_scores'] = category_scores
        context['widget']['value'] = json.dumps(category_scores_dict)
        return context
    
    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(render_to_string(self.template_name, context))
    
    def value_from_datadict(self, data, files, name):
        """form 데이터에서 값 추출"""
        # 폼에서 제출된 카테고리 점수 데이터 처리
        category_scores = {}
        
        for key, value in data.items():
            if key.startswith(f'{name}_category_'):
                # key 형식: name_category_ID
                category_id = key.split('_')[-1]
                try:
                    category = Category.objects.get(id=category_id)
                    score = int(value) if value else 0
                    if score != 0:  # 점수가 0인 경우 저장하지 않음
                        category_scores[category.name] = score
                except (Category.DoesNotExist, ValueError):
                    pass
        
        return json.dumps(category_scores) if category_scores else '{}'