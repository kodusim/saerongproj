from django.contrib import admin
from .models import FaceTestModel

@admin.register(FaceTestModel)
class FaceTestModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
        ('모델 파일', {
            'fields': ('model_file', 'result_types_file'),
            'description': '필수 모델 파일을 업로드하세요.'
        }),
        ('스크립트 파일', {
            'fields': ('train_script', 'predict_script'),
            'description': '(선택사항) 학습 및 예측용 스크립트 파일을 업로드하세요.'
        }),
    )