from django.contrib.admin import helpers
from django.contrib.admin.options import InlineModelAdmin
from django.forms.formsets import DELETION_FIELD_NAME

class NestedInlineMixin:
    """중첩 인라인 구현을 위한 믹스인"""
    
    def get_formset(self, request, obj=None, **kwargs):
        """인라인 폼셋 가져오기"""
        formset = super().get_formset(request, obj, **kwargs)
        formset.parent_model = self.parent_model
        return formset

class NestedStackedInline(NestedInlineMixin, InlineModelAdmin):
    """중첩된 스택 형식의 인라인 구현"""
    template = 'admin/edit_inline/stacked.html'
    
class NestedTabularInline(NestedInlineMixin, InlineModelAdmin):
    """중첩된 테이블 형식의 인라인 구현"""
    template = 'admin/edit_inline/tabular.html'