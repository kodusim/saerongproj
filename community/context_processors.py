from .models import BoardCategory

def community_categories(request):
    """모든 활성화된 카테고리를 모든 템플릿에 제공하는 컨텍스트 프로세서"""
    categories = BoardCategory.objects.filter(is_active=True).order_by('order', 'name')
    return {
        'categories': categories
    }