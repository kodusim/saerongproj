from django import template
from urllib.parse import unquote

register = template.Library()

@register.filter
def urldecode(value):
    """URL 디코딩을 수행하는 템플릿 필터"""
    return unquote(value)