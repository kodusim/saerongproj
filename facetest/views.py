from django.shortcuts import render
from .models import FaceTestModel  # 여기를 수정했습니다

def index(request):
    """얼굴상 테스트 메인 페이지"""
    return render(request, 'facetest/index.html')