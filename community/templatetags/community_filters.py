from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def time_since(value):
    """
    사용자 친화적인 시간 표시 필터
    예: '2분 전', '3시간 전', '어제', '3일 전', '2023-04-26'
    """
    now = timezone.now()
    diff = now - value
    
    if diff < timedelta(minutes=1):
        return '방금 전'
    elif diff < timedelta(hours=1):
        minutes = diff.seconds // 60
        return f"{minutes}분 전"
    elif diff < timedelta(days=1):
        hours = diff.seconds // 3600
        return f"{hours}시간 전"
    elif diff < timedelta(days=2):
        return '어제'
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days}일 전"
    else:
        return value.strftime("%Y-%m-%d")