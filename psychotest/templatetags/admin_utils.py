import json
from django import template

register = template.Library()

@register.filter
def get_category_score(category_scores, category_name):
    """템플릿에서 카테고리별 점수를 가져오는 필터"""
    if not category_scores:
        return 0
    
    if isinstance(category_scores, str):
        try:
            category_scores = json.loads(category_scores)
        except json.JSONDecodeError:
            return 0
    
    return category_scores.get(category_name, 0)