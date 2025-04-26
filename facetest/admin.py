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
        return format_html(
            """
            <div style="display: flex; gap: 10px;">
                <div id="image-drag-zone-{0}" class="drag-zone" style="flex: 1; padding: 10px; text-align: center; background-color: #73b6d1; color: white; border-radius: 5px; cursor: pointer;">
                    <span style="font-weight: bold;">이미지 드래그</span>
                    <input type="file" id="image-upload-{0}" style="display: none;" multiple accept="image/*">
                </div>
                <div id="sub-image-drag-zone-{0}" class="drag-zone" style="flex: 1; padding: 10px; text-align: center; background-color: #6daebd; color: white; border-radius: 5px; cursor: pointer;">
                    <span style="font-weight: bold;">보조 이미지 드래그</span>
                    <input type="file" id="sub-image-upload-{0}" style="display: none;" accept="image/*">
                </div>
            </div>
            <script>
                (function() {{
                    // 1. 일반 이미지 드래그 영역 이벤트 설정
                    var dragZone = document.getElementById('image-drag-zone-{0}');
                    var fileInput = document.getElementById('image-upload-{0}');
                    
                    // 클릭시 파일 선택 대화상자 표시
                    dragZone.addEventListener('click', function() {{
                        fileInput.click();
                    }});
                    
                    // 드래그 앤 드롭 이벤트
                    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(function(event) {{
                        dragZone.addEventListener(event, function(e) {{
                            e.preventDefault();
                            e.stopPropagation();
                        }});
                    }});
                    
                    // 드래그 진입/오버 스타일 변경
                    ['dragenter', 'dragover'].forEach(function(event) {{
                        dragZone.addEventListener(event, function() {{
                            this.style.opacity = '0.8';
                        }});
                    }});
                    
                    // 드래그 나가기/드롭 스타일 복원
                    ['dragleave', 'drop'].forEach(function(event) {{
                        dragZone.addEventListener(event, function() {{
                            this.style.opacity = '1';
                        }});
                    }});
                    
                    // 파일 드롭 처리
                    dragZone.addEventListener('drop', function(e) {{
                        var files = e.dataTransfer.files;
                        handleImageFiles(files);
                    }});
                    
                    // 파일 선택 처리
                    fileInput.addEventListener('change', function() {{
                        handleImageFiles(this.files);
                    }});
                    
                    // 파일 업로드 처리 함수
                    function handleImageFiles(files) {{
                        if (!files.length) return;
                        
                        // FormData 객체 생성
                        var formData = new FormData();
                        
                        // 여러 파일 처리
                        for (var i = 0; i < files.length; i++) {{
                            formData.append('image', files[i]);
                            formData.append('title', files[i].name);
                        }}
                        
                        // CSRF 토큰 가져오기
                        var csrfTokenValue = document.querySelector('[name=csrfmiddlewaretoken]').value;
                        
                        // 업로드 요청 전송
                        fetch('/facetest/admin/result-type/{0}/upload-image/', {{
                            method: 'POST',
                            body: formData,
                            headers: {{
                                'X-CSRFToken': csrfTokenValue
                            }}
                        }})
                        .then(function(response) {{ return response.json(); }})
                        .then(function(data) {{
                            if (data.success) {{
                                alert('이미지가 성공적으로 업로드되었습니다.');
                                location.reload();
                            }} else {{
                                alert('업로드 실패: ' + (data.message || '알 수 없는 오류'));
                            }}
                        }})
                        .catch(function(error) {{
                            alert('업로드 중 오류 발생: ' + error);
                        }});
                    }}
                    
                    // 2. 보조 이미지 드래그 영역 이벤트 설정
                    var subDragZone = document.getElementById('sub-image-drag-zone-{0}');
                    var subFileInput = document.getElementById('sub-image-upload-{0}');
                    
                    // 클릭시 파일 선택 대화상자 표시
                    subDragZone.addEventListener('click', function() {{
                        subFileInput.click();
                    }});
                    
                    // 드래그 앤 드롭 이벤트
                    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(function(event) {{
                        subDragZone.addEventListener(event, function(e) {{
                            e.preventDefault();
                            e.stopPropagation();
                        }});
                    }});
                    
                    // 드래그 진입/오버 스타일 변경
                    ['dragenter', 'dragover'].forEach(function(event) {{
                        subDragZone.addEventListener(event, function() {{
                            this.style.opacity = '0.8';
                        }});
                    }});
                    
                    // 드래그 나가기/드롭 스타일 복원
                    ['dragleave', 'drop'].forEach(function(event) {{
                        subDragZone.addEventListener(event, function() {{
                            this.style.opacity = '1';
                        }});
                    }});
                    
                    // 파일 드롭 처리
                    subDragZone.addEventListener('drop', function(e) {{
                        var files = e.dataTransfer.files;
                        if (files.length > 0) {{
                            handleSubImageFile(files[0]); // 첫 번째 파일만 처리
                        }}
                    }});
                    
                    // 파일 선택 처리
                    subFileInput.addEventListener('change', function() {{
                        if (this.files.length > 0) {{
                            handleSubImageFile(this.files[0]); // 첫 번째 파일만 처리
                        }}
                    }});
                    
                    // 보조 이미지 파일 업로드 처리 함수
                    function handleSubImageFile(file) {{
                        // FormData 객체 생성
                        var formData = new FormData();
                        formData.append('sub_image', file);
                        
                        // CSRF 토큰 가져오기
                        var csrfTokenValue = document.querySelector('[name=csrfmiddlewaretoken]').value;
                        
                        // 업로드 요청 전송 - URL 경로가 올바른지 확인
                        fetch('/facetest/admin/result-type/{0}/update-sub-image/', {{
                            method: 'POST',
                            body: formData,
                            headers: {{
                                'X-CSRFToken': csrfTokenValue
                            }}
                        }})
                        .then(function(response) {{ 
                            console.log("응답 상태:", response.status);
                            return response.json(); 
                        }})
                        .then(function(data) {{
                            console.log("응답 데이터:", data);
                            if (data.success) {{
                                alert('보조 이미지가 성공적으로 업로드되었습니다.');
                                location.reload();
                            }} else {{
                                alert('업로드 실패: ' + (data.error || '알 수 없는 오류'));
                            }}
                        }})
                        .catch(function(error) {{
                            console.error("업로드 오류:", error);
                            alert('업로드 중 오류 발생: ' + error);
                        }});
                    }}
                }})();
            </script>
            """,
            obj.id
        )
    upload_image_button.short_description = "이미지 관리"

    def upload_sub_image_view(self, request, result_type_id):
        """보조 이미지 업로드 대화상자 뷰"""
        result_type = get_object_or_404(FaceResultType, id=result_type_id)
        
        return render(request, 'admin/facetest/upload_sub_image.html', {
            'result_type': result_type,
            'opts': self.model._meta,
            'title': f"{result_type.name} - 보조 이미지 업로드",
        })
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
            path('<int:result_type_id>/upload-sub-image/', 
                self.admin_site.admin_view(self.upload_sub_image_view), 
                name='facetest_upload_sub_image'),
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
        
        # 결과 유형 목록 준비
        queryset = self.get_queryset(request)
        result_type_options = ''.join([f'<option value="{rt.id}">{rt.name}</option>' for rt in queryset])
        
        # 이미지 업로드/관리를 위한 JavaScript 코드 추가
        extra_context['extra_js'] = f"""
        <style>
            .upload-zone {{
                border: 2px dashed #ccc;
                padding: 20px;
                text-align: center;
                margin: 10px 0;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s ease;
                display: none;
            }}
            
            .upload-zone.highlight {{
                border-color: #28a745;
                background-color: #f8f9fa;
            }}
            
            .progress {{
                margin-top: 10px;
                height: 20px;
                display: none;
                background: #f0f0f0;
                border-radius: 4px;
                overflow: hidden;
            }}
            
            .progress-bar {{
                height: 100%;
                background-color: #28a745;
                width: 0%;
                transition: width 0.3s;
                text-align: center;
                color: white;
                line-height: 20px;
                font-size: 12px;
            }}
            
            .upload-message {{
                margin-top: 10px;
                padding: 10px;
                border-radius: 4px;
                display: none;
            }}
            
            .upload-message.success {{
                background-color: #d4edda;
                color: #155724;
            }}
            
            .upload-message.error {{
                background-color: #f8d7da;
                color: #721c24;
            }}
        </style>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // 디버깅 출력 추가
            console.log("드래그 앤 드롭 스크립트 로드됨");
            
            // 계산한 CSRF 토큰 - Django에서 자동으로 생성됨
            var csrfToken = '{{% csrf_token %}}'.match(/value=['"]([^'"]*)['"]/)[1];
            
            // 더 확실한 위치 선택 (여러 가능한 위치 시도)
            var targetElements = [
                document.getElementById('changelist-form'),  // 기본 changelist 폼
                document.querySelector('.actions'),  // 액션 바
                document.querySelector('#content-main'),  // 메인 콘텐츠 영역
                document.querySelector('form#changelist-form')  // ID와 태그로 선택
            ];
            
            // 사용 가능한 첫 번째 요소 선택
            var targetElement = null;
            for (var i = 0; i < targetElements.length; i++) {{
                if (targetElements[i]) {{
                    targetElement = targetElements[i];
                    console.log("타겟 요소 발견:", i);
                    break;
                }}
            }}
            
            if (!targetElement) {{
                console.error("업로드 영역을 추가할 대상 요소를 찾을 수 없습니다.");
                return;
            }}
            
            // 버튼과 선택기 추가
            var controlDiv = document.createElement('div');
            controlDiv.className = 'upload-controls';
            controlDiv.style.marginBottom = '15px';
            controlDiv.style.marginTop = '15px';
            controlDiv.innerHTML = `
                <button type="button" id="toggle-upload-zone" class="button">드래그 앤 드롭 업로드 영역 표시</button>
                <select id="result-type-selector" style="margin-left: 10px; display: none;">
                    <option value="">-- 결과 유형 선택 --</option>
                    {result_type_options}
                </select>
            `;
            
            // 타겟 요소 맨 앞에 삽입
            targetElement.parentNode.insertBefore(controlDiv, targetElement);
            
            // 업로드 영역 추가
            var uploadZone = document.createElement('div');
            uploadZone.className = 'upload-zone';
            uploadZone.id = 'upload-zone';
            uploadZone.innerHTML = `
                <p>이미지 파일을 여기에 드래그하거나 클릭하여 업로드하세요</p>
                <input type="file" id="file-upload" style="display: none;" multiple accept="image/*">
                <div class="progress">
                    <div class="progress-bar" id="progress-bar">0%</div>
                </div>
                <div class="upload-message" id="upload-message"></div>
            `;
            
            targetElement.parentNode.insertBefore(uploadZone, targetElement.nextSibling);
            
            console.log("업로드 영역 추가됨");
            
            // 토글 버튼 이벤트
            var toggleBtn = document.getElementById('toggle-upload-zone');
            var resultSelector = document.getElementById('result-type-selector');
            var fileInput = document.getElementById('file-upload');
            
            if (toggleBtn) {{
                toggleBtn.addEventListener('click', function() {{
                    var zone = document.getElementById('upload-zone');
                    if (!zone) {{
                        console.error("업로드 영역 요소를 찾을 수 없습니다.");
                        return;
                    }}
                    
                    if (zone.style.display === 'none' || !zone.style.display) {{
                        zone.style.display = 'block';
                        resultSelector.style.display = 'inline-block';
                        this.textContent = '업로드 영역 숨기기';
                    }} else {{
                        zone.style.display = 'none';
                        resultSelector.style.display = 'none';
                        this.textContent = '드래그 앤 드롭 업로드 영역 표시';
                    }}
                    
                    console.log("토글 버튼 클릭됨, 영역 표시:", zone.style.display);
                }});
            }} else {{
                console.error("토글 버튼을 찾을 수 없습니다.");
            }}
            
            // 파일 업로드 처리
            var uploadZone = document.getElementById('upload-zone');
            
            if (uploadZone && fileInput) {{
                uploadZone.addEventListener('click', function() {{
                    fileInput.click();
                }});
                
                // 드래그 앤 드롭 이벤트
                ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(function(event) {{
                    uploadZone.addEventListener(event, preventDefaults, false);
                }});
                
                function preventDefaults(e) {{
                    e.preventDefault();
                    e.stopPropagation();
                }}
                
                ['dragenter', 'dragover'].forEach(function(event) {{
                    uploadZone.addEventListener(event, function() {{
                        uploadZone.classList.add('highlight');
                    }}, false);
                }});
                
                ['dragleave', 'drop'].forEach(function(event) {{
                    uploadZone.addEventListener(event, function() {{
                        uploadZone.classList.remove('highlight');
                    }}, false);
                }});
                
                uploadZone.addEventListener('drop', function(e) {{
                    console.log("파일 드롭됨");
                    var files = e.dataTransfer.files;
                    handleFiles(files);
                }});
                
                fileInput.addEventListener('change', function() {{
                    console.log("파일 선택됨");
                    handleFiles(this.files);
                }});
            }} else {{
                console.error("업로드 영역 또는 파일 입력 요소를 찾을 수 없습니다.");
            }}
            
            function handleFiles(files) {{
                var resultTypeSelector = document.getElementById('result-type-selector');
                if (!resultTypeSelector) {{
                    console.error("결과 유형 선택기를 찾을 수 없습니다.");
                    return;
                }}
                
                var resultTypeId = resultTypeSelector.value;
                
                if (!resultTypeId) {{
                    showMessage('결과 유형을 선택해주세요', 'error');
                    return;
                }}
                
                var progressBar = document.getElementById('progress-bar');
                var progressContainer = document.querySelector('.progress');
                
                if (!progressBar || !progressContainer) {{
                    console.error("진행 표시줄 요소를 찾을 수 없습니다.");
                    return;
                }}
                
                // 진행 표시줄 초기화 및 표시
                progressBar.style.width = '0%';
                progressBar.textContent = '0%';
                progressContainer.style.display = 'block';
                
                var uploadedCount = 0;
                var totalFiles = files.length;
                
                console.log("업로드 시작, 총 파일 수:", totalFiles);
                
                Array.from(files).forEach(function(file) {{
                    uploadFile(file, resultTypeId, function(success) {{
                        uploadedCount++;
                        
                        // 진행률 업데이트
                        var percent = Math.round((uploadedCount / totalFiles) * 100);
                        progressBar.style.width = percent + '%';
                        progressBar.textContent = percent + '%';
                        
                        console.log("파일 업로드 완료:", file.name, "성공:", success, "진행:", percent + "%");
                        
                        // 모든 파일 업로드 완료 시
                        if (uploadedCount === totalFiles) {{
                            showMessage(totalFiles + '개의 이미지가 성공적으로 업로드되었습니다.', 'success');
                            
                            // 3초 후 페이지 새로고침
                            setTimeout(function() {{
                                location.reload();
                            }}, 3000);
                        }}
                    }});
                }});
            }}
            
            function uploadFile(file, resultTypeId, callback) {{
                // 이미지 파일인지 확인
                if (!file.type.match('image.*')) {{
                    showMessage(file.name + '은(는) 이미지 파일이 아닙니다.', 'error');
                    callback(false);
                    return;
                }}
                
                var formData = new FormData();
                formData.append('image', file);
                formData.append('title', file.name);
                
                // CSRF 토큰 가져오기 - 여러 방법 시도
                var csrfToken = '';
                var csrfField = document.querySelector('input[name="csrfmiddlewaretoken"]');
                
                if (csrfField) {{
                    csrfToken = csrfField.value;
                }} else {{
                    // Django에서 제공하는 쿠키에서 CSRF 토큰 가져오기
                    var cookies = document.cookie.split(';');
                    for (var i = 0; i < cookies.length; i++) {{
                        var cookie = cookies[i].trim();
                        if (cookie.startsWith('csrftoken=')) {{
                            csrfToken = cookie.substring('csrftoken='.length);
                            break;
                        }}
                    }}
                }}
                
                console.log("파일 업로드 요청:", file.name, "결과 유형 ID:", resultTypeId, "CSRF 토큰 존재:", !!csrfToken);
                
                fetch('/facetest/admin/result-type/' + resultTypeId + '/upload-image/', {{
                    method: 'POST',
                    body: formData,
                    headers: {{
                        'X-CSRFToken': csrfToken
                    }}
                }})
                .then(function(response) {{ 
                    console.log("응답 상태:", response.status);
                    return response.json(); 
                }})
                .then(function(data) {{
                    console.log("응답 데이터:", data);
                    if (data.success) {{
                        callback(true);
                    }} else {{
                        var errorMsg = data.message || data.error || '업로드 실패';
                        showMessage(file.name + ' 업로드 실패: ' + errorMsg, 'error');
                        callback(false);
                    }}
                }})
                .catch(function(error) {{
                    console.error("업로드 오류:", error);
                    showMessage(file.name + ' 업로드 중 오류 발생: ' + error, 'error');
                    callback(false);
                }});
            }}
            
            function showMessage(text, type) {{
                var messageContainer = document.getElementById('upload-message');
                if (!messageContainer) {{
                    console.error("메시지 컨테이너를 찾을 수 없습니다.");
                    alert(text);
                    return;
                }}
                
                messageContainer.textContent = text;
                messageContainer.className = 'upload-message ' + type;
                messageContainer.style.display = 'block';
                
                console.log("메시지 표시:", text, "타입:", type);
                
                if (type === 'error') {{
                    setTimeout(function() {{
                        messageContainer.style.display = 'none';
                    }}, 5000);
                }}
            }}
            
            // 기존 함수 유지
            window.showImageUploadDialog = function(event, url) {{
                event.preventDefault();
                
                var width = 600;
                var height = 400;
                var left = (screen.width/2) - (width/2);
                var top = (screen.height/2) - (height/2);
                
                window.open(
                    url, 
                    '이미지 업로드',
                    'width=' + width + ',height=' + height + ',top=' + top + ',left=' + left + ',resizable=yes,scrollbars=yes'
                );
                
                return false;
            }};
            
            window.showImagesDialog = function(event, url) {{
                event.preventDefault();
                
                var width = 800;
                var height = 600;
                var left = (screen.width/2) - (width/2);
                var top = (screen.height/2) - (height/2);
                
                window.open(
                    url, 
                    '이미지 관리',
                    'width=' + width + ',height=' + height + ',top=' + top + ',left=' + left + ',resizable=yes,scrollbars=yes'
                );
                
                return false;
            }};
        }});
        </script>
        """
        
        return super().changelist_view(request, extra_context)


@admin.register(FaceTestModel)
class FaceTestModelAdmin(admin.ModelAdmin):
    """얼굴상 테스트 모델 관리자"""
    list_display = ['name', 'show_thumbnail', 'is_active', 'view_count', 'created_at', 'result_types_count', 'view_result_types']
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