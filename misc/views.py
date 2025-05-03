from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import FortuneType, FortuneCategory, FortuneContent, UserFortune, UserFortuneResult
import random
from datetime import date

def home(request):
    """잡동사니 앱 홈페이지"""
    fortune_types = FortuneType.objects.filter(is_active=True).order_by('order')
    
    context = {
        'title': '잡동사니',
        'description': '다양한 미니 콘텐츠를 즐겨보세요!',
        'fortune_types': fortune_types,
    }
    return render(request, 'misc/home.html', context)

def get_or_create_daily_fortune(user=None, session_id=None, fortune_type=None):
    """
    사용자 또는 세션별 오늘의 운세를 조회하거나 생성
    """
    today = date.today()
    
    # 사용자 또는 세션ID로 오늘 이미 생성된 운세가 있는지 확인
    user_fortune = None
    if user and user.is_authenticated:
        user_fortune = UserFortune.objects.filter(
            user=user, 
            fortune_type=fortune_type, 
            date=today
        ).first()
    elif session_id:
        user_fortune = UserFortune.objects.filter(
            session_id=session_id, 
            fortune_type=fortune_type, 
            date=today
        ).first()
    
    # 이미 있으면 기존 것 반환
    if user_fortune:
        return user_fortune
    
    # 없으면 새로 생성
    user_fortune = UserFortune.objects.create(
        user=user if user and user.is_authenticated else None,
        session_id=session_id if not (user and user.is_authenticated) else "",
        fortune_type=fortune_type,
        date=today
    )
    
    # 활성화된 모든 카테고리 가져오기
    categories = FortuneCategory.objects.filter(is_active=True).order_by('order')
    
    for category in categories:
        # 각 카테고리별로 적절한 레벨의 운세 콘텐츠를 하나 선택
        # 무작위 번호 생성 방식 (완전 랜덤)
        level = random.randint(1, 5)
        
        # 각 카테고리별로 해당 레벨의 운세 내용 가져오기
        contents = FortuneContent.objects.filter(
            fortune_type=fortune_type, 
            category=category, 
            level=level,
            is_active=True
        )
        
        # 내용이 있으면 하나 선택하여 결과 저장
        if contents.exists():
            selected_content = random.choice(list(contents))
            UserFortuneResult.objects.create(
                user_fortune=user_fortune,
                category=category,
                content=selected_content
            )
    
    return user_fortune

def fortune_home(request):
    """운세 메인 페이지"""
    fortune_types = FortuneType.objects.filter(is_active=True).order_by('order')
    
    context = {
        'fortune_types': fortune_types,
    }
    return render(request, 'misc/fortune/home.html', context)

def daily_fortune(request, slug):
    """일일 운세 보기"""
    try:
        fortune_type = FortuneType.objects.get(slug=slug, is_active=True)
    except FortuneType.DoesNotExist:
        messages.error(request, '존재하지 않는 운세 유형입니다.')
        return redirect('misc:fortune_home')
    
    # 서비스 준비 안된 경우
    if not fortune_type.is_ready:
        return render(request, 'misc/fortune/coming_soon.html', {'fortune_type': fortune_type})
    
    # 사용자 정보 확인
    user = request.user
    session_id = request.session.session_key
    
    # 세션 ID가 없으면 생성
    if not session_id:
        request.session.create()
        session_id = request.session.session_key
    
    # 오늘의 운세 가져오기
    fortune = get_or_create_daily_fortune(user, session_id, fortune_type)
    
    # 결과 가져오기
    results = fortune.results.all().select_related('category', 'content')
    
    context = {
        'fortune_type': fortune_type,
        'fortune_date': fortune.date,
        'results': results,
    }
    
    return render(request, 'misc/fortune/daily_fortune.html', context)