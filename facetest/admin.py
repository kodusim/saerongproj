from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
import json
import os
from django.core.files.base import ContentFile
from django.conf import settings

from .models import FaceModel, FaceType, FaceTestResult

class FaceTypeInline(admin.TabularInline):
    model = FaceType
    extra = 0
    fields = ['name', 'code', 'description', 'image_preview']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "이미지 없음"
    image_preview.short_description = '이미지'

@admin.register(FaceModel)
class FaceModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'created_at', 'face_types_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    inlines = [FaceTypeInline]
    actions = ['activate_model']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:model_id>/import-types/', 
                 self.admin_site.admin_view(self.import_face_types),
                 name='import-face-types'),
        ]
        return custom_urls + urls
    
    def import_face_types(self, request, model_id):
        """얼굴 유형 JSON 파일에서 일괄 가져오기"""
        face_model = FaceModel.objects.get(id=model_id)
        
        if request.method == 'POST':
            json_file = request.FILES.get('json_file')
            
            if not json_file:
                messages.error(request, "JSON 파일을 선택해주세요.")
                return HttpResponseRedirect(reverse('admin:facetest_facemodel_change', args=[model_id]))
            
            try:
                # JSON 파일 파싱
                json_data = json.load(json_file)
                
                # 얼굴 유형 일괄 생성
                created_count = 0
                updated_count = 0
                
                for type_code, type_info in json_data.items():
                    # 기존 유형이 있는지 확인
                    face_type, created = FaceType.objects.update_or_create(
                        model=face_model,
                        code=type_code,
                        defaults={
                            'name': type_info.get('name', type_code),
                            'description': type_info.get('description', f'{type_code} 유형입니다.'),
                            'characteristics': '\n'.join(type_info.get('characteristics', [])),
                            'examples': '\n'.join(type_info.get('examples', []))
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                
                # 결과 메시지
                if created_count > 0 or updated_count > 0:
                    messages.success(
                        request, 
                        f"{created_count}개의 얼굴 유형이 생성되고, {updated_count}개의 얼굴 유형이 업데이트되었습니다."
                    )
                else:
                    messages.info(request, "처리된 얼굴 유형이 없습니다.")
                
            except Exception as e:
                messages.error(request, f"얼굴 유형 가져오기 오류: {str(e)}")
            
            return HttpResponseRedirect(reverse('admin:facetest_facemodel_change', args=[model_id]))
        
        # GET 요청 처리
        context = {
            'title': '얼굴 유형 일괄 가져오기',
            'opts': self.model._meta,
            'face_model': face_model,
            'media': self.media,
        }
        return render(request, 'admin/facetest/facemodel/import_face_types.html', context)
    
    def face_types_count(self, obj):
        return obj.face_types.count()
    face_types_count.short_description = '얼굴 유형 수'
    
    def activate_model(self, request, queryset):
        # 선택된 모델 활성화
        if queryset.count() > 1:
            messages.warning(request, "한 번에 하나의 모델만 활성화할 수 있습니다. 첫 번째 선택된 모델만 활성화합니다.")
        
        # 모든 모델을 비활성화
        FaceModel.objects.all().update(is_active=False)
        
        # 선택된 첫 번째 모델 활성화
        model = queryset.first()
        model.is_active = True
        model.save()
        
        messages.success(request, f"'{model.name}' 모델이 활성화되었습니다.")
    activate_model.short_description = "선택된 모델 활성화"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_import_button'] = True
        return super().change_view(request, object_id, form_url, extra_context)

    def response_change(self, request, obj):
        """관리자 페이지 저장 이후 처리"""
        if "_import_face_types" in request.POST:
            # 여기서 URL 이름이 위에서 정의한 이름과 일치해야 함
            return HttpResponseRedirect(
                reverse('admin:facetest_facemodel_import_types', args=[obj.id])
            )
        return super().response_change(request, obj)

@admin.register(FaceType)
class FaceTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'model', 'image_preview']
    list_filter = ['model']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['image_full']
    
    fieldsets = (
        (None, {
            'fields': ('model', 'name', 'code', 'description')
        }),
        ('이미지', {
            'fields': ('image', 'image_full')
        }),
        ('상세 정보', {
            'fields': ('characteristics', 'examples'),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "이미지 없음"
    image_preview.short_description = '이미지'
    
    def image_full(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="300" />', obj.image.url)
        return "이미지 없음"
    image_full.short_description = '이미지 (원본)'

@admin.register(FaceTestResult)
class FaceTestResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'face_type', 'probability_percent', 'created_at', 'image_preview']
    list_filter = ['face_type', 'created_at']
    readonly_fields = ['id', 'image', 'face_type', 'probability', 'all_results', 'created_at', 'image_full']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "이미지 없음"
    image_preview.short_description = '이미지'
    
    def image_full(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="300" />', obj.image.url)
        return "이미지 없음"
    image_full.short_description = '이미지 (원본)'
    
    def probability_percent(self, obj):
        return f"{obj.probability:.1%}"
    probability_percent.short_description = '확률'
    
    def has_add_permission(self, request):
        # 관리자 페이지에서 직접 추가 방지 (사용자 테스트 결과만 저장)
        return False