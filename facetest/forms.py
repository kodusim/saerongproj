from django import forms
from .models import FaceTestResult

class FaceImageUploadForm(forms.Form):
    """얼굴 이미지 업로드 폼"""
    image = forms.ImageField(
        label='얼굴 이미지', 
        help_text='정면 얼굴이 나온 사진을 업로드하세요.',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'data-upload-label': '이미지 선택',
        })
    )

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # 파일 크기 검증 (10MB 제한)
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError("이미지 크기는 10MB를 초과할 수 없습니다.")
                
            # 파일 확장자 검증
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp']
            ext = image.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise forms.ValidationError(f"지원되는 이미지 형식: {', '.join(allowed_extensions)}")
        
        return image


class FaceModelAdminForm(forms.ModelForm):
    """관리자 페이지용 얼굴상 모델 폼"""
    import_types = forms.FileField(
        label='얼굴 유형 JSON',
        required=False,
        help_text='얼굴 유형 정보를 포함한 JSON 파일(face_types.json)을 업로드하세요.',
        widget=forms.FileInput(attrs={'accept': '.json'})
    )