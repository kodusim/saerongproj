from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages

from .models import FaceTestModel, FaceResultType, FaceResultImage


class FaceResultImageInline(admin.TabularInline):
    """결과 유형별 이미지 인라인"""
    model = FaceResultImage
    extra = 1
    fields = ('image', 'image_preview', 'title', 'order', 'is_main')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', obj.image.url)
        return "이미지 없음"
    image_preview.short_description = "이미지 미리보기"


class FaceResultTypeInline(admin.TabularInline):
    """얼굴상 결과 유형 인라인"""
    model = FaceResultType
    extra = 0
    fields = ('type_id', 'name', 'description', 'view_detail')
    readonly_fields = ('type_id', 'name', 'description', 'view_detail')
    show_change_link = True
    can_delete = False
    max_num = 0  # 추가/삭제 불가능
    
    def view_detail(self, obj):
        if obj.pk:
            url = reverse('admin:facetest_faceresulttype_change', args=[obj.pk])
            return format_html('<a href="{}">결과 유형 상세보기</a>', url)
        return "-"
    view_detail.short_description = "상세보기"


@admin.register(FaceResultType)
class FaceResultTypeAdmin(admin.ModelAdmin):
    """얼굴상 결과 유형 관리자"""
    list_display = ['type_id', 'name', 'face_test', 'short_description', 'preview_image', 'upload_image_button']
    list_filter = ['face_test']
    search_fields = ['name', 'description']
    inlines = [FaceResultImageInline]
    actions = ['bulk_image_upload']
    
    # 필드셋에 배경색과 보조 이미지 필드 추가
    fieldsets = (
        (None, {
            'fields': ('face_test', 'type_id', 'name', 'description')
        }),
        ('스타일', {
            'fields': ('background_color', 'sub_image', 'sub_image_preview'),
            'description': '결과 페이지의 배경색과 보조 이미지를 설정합니다.'
        }),
        ('데이터', {
            'fields': ('characteristics', 'examples'),
            'description': '특성과 예시는 JSON 형식으로 저장됩니다. 리스트 형식([])으로 입력하세요.'
        }),
    )
    readonly_fields = ('sub_image_preview',)
    
    def sub_image_preview(self, obj):
        """보조 이미지 미리보기"""
        if obj.sub_image:
            return format_html('<img src="{}" width="300" style="max-height: 200px; object-fit: contain;" />', obj.sub_image.url)
        return "보조 이미지 없음"
    sub_image_preview.short_description = "보조 이미지 미리보기"
    
    def short_description(self, obj):
        if len(obj.description) > 50:
            return obj.description[:50] + "..."
        return obj.description
    short_description.short_description = "설명"
    
    def preview_image(self, obj):
        """대표 이미지 미리보기"""
        main_image = obj.images.filter(is_main=True).first()
        if main_image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 5px;" />', main_image.image.url)
        elif obj.images.exists():
            image = obj.images.first()
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 5px;" />', image.image.url)
        return "(이미지 없음)"
    preview_image.short_description = "이미지 미리보기"
    
    def upload_image_button(self, obj):
        """이미지 업로드 버튼"""
        upload_url = reverse('admin:facetest_upload_image', args=[obj.id])
        view_url = reverse('admin:facetest_view_images', args=[obj.id])
        
        return format_html(
            '<a href="{}" class="button" onclick="return showImageUploadDialog(event, \'{}\')">이미지 업로드</a>'
            '&nbsp;'
            '<a href="{}" class="button" onclick="return showImagesDialog(event, \'{}\')">이미지 보기</a>',
            upload_url, upload_url, view_url, view_url
        )
    upload_image_button.short_description = "이미지 관리"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:result_type_id>/upload-image/', 
                self.admin_site.admin_view(self.upload_image_view), 
                name='facetest_upload_image'),
            path('<int:result_type_id>/view-images/', 
                self.admin_site.admin_view(self.view_images), 
                name='facetest_view_images'),
            path('<int:result_type_id>/save-image/', 
                self.admin_site.admin_view(self.save_image), 
                name='facetest_save_image'),
            path('image/<int:image_id>/delete/', 
                self.admin_site.admin_view(self.delete_image), 
                name='facetest_delete_image'),
            path('image/<int:image_id>/set-main/', 
                self.admin_site.admin_view(self.set_main_image), 
                name='facetest_set_main_image'),
        ]
        return custom_urls + urls
    
    def upload_image_view(self, request, result_type_id):
        """이미지 업로드 대화상자 뷰"""
        result_type = get_object_or_404(FaceResultType, id=result_type_id)
        
        return render(request, 'admin/facetest/upload_image.html', {
            'result_type': result_type,
            'opts': self.model._meta,
            'title': f"{result_type.name} - 이미지 업로드",
        })
    
    def view_images(self, request, result_type_id):
        """이미지 목록 보기 뷰"""
        result_type = get_object_or_404(FaceResultType, id=result_type_id)
        images = result_type.images.all().order_by('-is_main', 'order')
        
        return render(request, 'admin/facetest/view_images.html', {
            'result_type': result_type,
            'images': images,
            'opts': self.model._meta,
            'title': f"{result_type.name} - 이미지 관리",
        })
    
    def save_image(self, request, result_type_id):
        """이미지 저장 처리"""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'message': '잘못된 요청 방식입니다.'})
        
        result_type = get_object_or_404(FaceResultType, id=result_type_id)
        
        try:
            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({'success': False, 'message': '이미지 파일이 제공되지 않았습니다.'})
            
            title = request.POST.get('title', '')
            is_main = request.POST.get('is_main') == 'true'
            
            # 이미지 생성
            result_image = FaceResultImage.objects.create(
                result_type=result_type,
                image=image_file,
                title=title,
                is_main=is_main
            )
            
            # 대표 이미지 설정 시 다른 이미지들의 대표 상태 해제
            if is_main:
                FaceResultImage.objects.filter(
                    result_type=result_type, 
                    is_main=True
                ).exclude(id=result_image.id).update(is_main=False)
            
            return JsonResponse({
                'success': True, 
                'image_id': result_image.id,
                'image_url': result_image.image.url
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    def delete_image(self, request, image_id):
        """이미지 삭제 처리"""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'message': '잘못된 요청 방식입니다.'})
        
        try:
            image = get_object_or_404(FaceResultImage, id=image_id)
            image.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    def set_main_image(self, request, image_id):
        """대표 이미지 설정 처리"""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'message': '잘못된 요청 방식입니다.'})
        
        try:
            image = get_object_or_404(FaceResultImage, id=image_id)
            result_type = image.result_type
            
            # 모든 이미지의 대표 상태 해제
            FaceResultImage.objects.filter(result_type=result_type, is_main=True).update(is_main=False)
            
            # 선택한 이미지를 대표로 설정
            image.is_main = True
            image.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    def bulk_image_upload(self, request, queryset):
        """일괄 이미지 업로드 액션"""
        if len(queryset) == 0:
            self.message_user(request, "선택된 결과 유형이 없습니다.", level=messages.ERROR)
            return
        
        return render(request, 'admin/facetest/bulk_upload.html', {
            'opts': self.model._meta,
            'title': "일괄 이미지 업로드",
            'result_types': queryset,
        })
    bulk_image_upload.short_description = "선택한 유형에 일괄 이미지 업로드"
    
    def changelist_view(self, request, extra_context=None):
        """목록 뷰에 JavaScript 추가"""
        extra_context = extra_context or {}
        
        # 이미지 업로드/관리를 위한 JavaScript 코드 추가
        extra_context['extra_js'] = """
        <script>
        function showImageUploadDialog(event, url) {
            event.preventDefault();
            
            // 모달 창 열기
            const width = 600;
            const height = 400;
            const left = (screen.width/2) - (width/2);
            const top = (screen.height/2) - (height/2);
            
            window.open(
                url, 
                '이미지 업로드',
                `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes`
            );
            
            return false;
        }
        
        function showImagesDialog(event, url) {
            event.preventDefault();
            
            // 모달 창 열기
            const width = 800;
            const height = 600;
            const left = (screen.width/2) - (width/2);
            const top = (screen.height/2) - (height/2);
            
            window.open(
                url, 
                '이미지 관리',
                `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes`
            );
            
            return false;
        }
        </script>
        """
        
        return super().changelist_view(request, extra_context)


@admin.register(FaceTestModel)
class FaceTestModelAdmin(admin.ModelAdmin):
    """얼굴상 테스트 모델 관리자"""
    list_display = ['name', 'show_thumbnail', 'is_active', 'created_at', 'result_types_count', 'view_result_types']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'sync_status', 'image_preview', 'intro_image_preview', 'guide_image_preview']
    inlines = [FaceResultTypeInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
        ('이미지', {
            'fields': ('image', 'image_preview', 'intro_image', 'intro_image_preview', 'guide_image', 'guide_image_preview'),
            'description': '메인 페이지 썸네일, 테스트 시작 페이지 이미지, 업로드 가이드 이미지를 업로드하세요.'
        }),
        ('가이드 텍스트', {
            'fields': ('upload_guide',),
            'description': '이미지 업로드 시 표시할 가이드 텍스트를 입력하세요.'
        }),
        ('모델 파일', {
            'fields': ('model_file', 'result_types_file', 'sync_status'),
            'description': '필수 모델 파일을 업로드하세요. 결과 유형 JSON 파일을 업로드하면 자동으로 결과 유형이 생성됩니다.'
        }),
        ('스크립트 파일', {
            'fields': ('train_script', 'predict_script'),
            'description': '(선택사항) 학습 및 예측용 스크립트 파일을 업로드하세요.'
        }),
        ('메타데이터', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def show_thumbnail(self, obj):
        """썸네일 표시"""
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "이미지 없음"
    show_thumbnail.short_description = '썸네일'
    
    def image_preview(self, obj):
        """이미지 미리보기"""
        if obj.image:
            return format_html('<img src="{}" width="200" />', obj.image.url)
        return "이미지 없음"
    image_preview.short_description = "썸네일 미리보기"
    
    def intro_image_preview(self, obj):
        """인트로 이미지 미리보기"""
        if obj.intro_image:
            return format_html('<img src="{}" width="300" />', obj.intro_image.url)
        return "이미지 없음"
    intro_image_preview.short_description = "인트로 이미지 미리보기"
    
    def guide_image_preview(self, obj):
        """가이드 이미지 미리보기"""
        if obj.guide_image:
            return format_html('<img src="{}" width="300" />', obj.guide_image.url)
        return "이미지 없음"
    guide_image_preview.short_description = "업로드 가이드 이미지 미리보기"
    
    def result_types_count(self, obj):
        count = obj.result_types.count()
        return count
    result_types_count.short_description = "결과 유형 수"
    
    def view_result_types(self, obj):
        if obj.pk:
            url = reverse('admin:facetest_faceresulttype_changelist') + f'?face_test__id__exact={obj.pk}'
            return format_html('<a href="{}">결과 유형 목록보기</a>', url)
        return "-"
    view_result_types.short_description = "결과 유형 보기"
    
    def manage_all_results(self, obj):
        """모든 결과 일괄 관리 링크"""
        if obj.pk:
            url = reverse('facetest:bulk_manage_result_types', args=[obj.pk])
            return format_html('<a href="{}" class="button">모든 결과 일괄 관리</a>', url)
        return "-"
    manage_all_results.short_description = "일괄 관리"
    
    def sync_status(self, obj):
        if not obj.pk or not obj.result_types_file:
            return "JSON 파일을 업로드하여 결과 유형을 생성하세요."
        
        count = obj.result_types.count()
        if count > 0:
            return format_html('결과 유형 {} 개 생성됨 <a href="#" class="button" onclick="document.getElementById(\'sync-form\').submit(); return false;">다시 동기화</a>', count)
        return "결과 유형이 생성되지 않았습니다. JSON 파일 형식을 확인하세요."
    sync_status.short_description = "동기화 상태"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/sync-results/', 
                self.admin_site.admin_view(self.sync_results_view), 
                name='facetest_facetestmodel_sync_results'),
        ]
        return custom_urls + urls
    
    def sync_results_view(self, request, object_id):
        """결과 유형 동기화 뷰"""
        face_test = get_object_or_404(FaceTestModel, pk=object_id)
        
        try:
            with transaction.atomic():
                face_test.sync_result_types()
            messages.success(request, f"결과 유형이 성공적으로 동기화되었습니다.")
        except Exception as e:
            messages.error(request, f"동기화 중 오류가 발생했습니다: {e}")
        
        return redirect('admin:facetest_facetestmodel_change', object_id=object_id)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """변경 뷰에 동기화 폼 추가"""
        extra_context = extra_context or {}
        extra_context['sync_form_url'] = reverse('admin:facetest_facetestmodel_sync_results', args=[object_id])
        return super().change_view(request, object_id, form_url, extra_context)
    
    def save_model(self, request, obj, form, change):
        """모델 저장 시 처리"""
        super().save_model(request, obj, form, change)
        
        # 결과 유형 파일이 변경되었으면 자동으로 동기화
        if 'result_types_file' in form.changed_data:
            try:
                obj.sync_result_types()
                messages.success(request, f"결과 유형 파일이 성공적으로 처리되었습니다.")
            except Exception as e:
                messages.error(request, f"결과 유형 파일 처리 중 오류가 발생했습니다: {e}")


# 결과 이미지 관리자 등록
@admin.register(FaceResultImage)
class FaceResultImageAdmin(admin.ModelAdmin):
    """얼굴상 결과 이미지 관리자"""
    list_display = ['result_type', 'title', 'is_main', 'image_preview', 'order', 'created_at']
    list_filter = ['result_type__face_test', 'result_type', 'is_main']
    search_fields = ['title', 'result_type__name']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" />', obj.image.url)
        return "이미지 없음"
    image_preview.short_description = "이미지 미리보기"