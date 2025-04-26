from django import forms
from django.contrib.auth import get_user_model
from .models import Post, Comment
from collections import OrderedDict

User = get_user_model()

class PostForm(forms.ModelForm):
    """게시글 작성/수정 폼"""
    
    # 관리자용 작성자 선택 필드 (관리자만 사용 가능)
    author = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='작성자'
    )
    
    class Meta:
        model = Post
        fields = ['title', 'content', 'image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '제목을 입력하세요'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': '내용을 입력하세요'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control-file'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 필드 순서 조정 - move_to_end 대신 alternative 방법 사용
        if 'author' in self.fields:
            # 필드 순서를 새로 정렬하는 방법
            author_field = self.fields.pop('author')
            new_fields = OrderedDict()
            new_fields['author'] = author_field
            for key, value in self.fields.items():
                new_fields[key] = value
            self.fields = new_fields
            
        # 이미지 필드 설명 추가
        self.fields['image'].help_text = '게시글에 표시할 이미지를 선택하세요. (선택사항)'


# 누락된 CommentForm 클래스 추가
class CommentForm(forms.ModelForm):
    """댓글 작성 폼"""
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '댓글을 입력하세요'
            })
        }