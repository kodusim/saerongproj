from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from psychotest.models import Test
from facetest.models import FaceTestModel
from community.models import Post
from .models import Banner
from django.http import HttpResponse
from django.views.decorators.http import require_GET

def root(request):
    """메인 페이지"""
    # 활성화된 배너 이미지 가져오기
    banners = Banner.objects.filter(is_active=True).order_by('order', '-created_at')
    
    # 최신 심리 테스트 가져오기
    recent_tests = Test.objects.all().order_by('-created_at')[:6]
    
    # 최신 얼굴상 테스트 가져오기
    recent_face_tests = FaceTestModel.objects.filter(is_active=True).order_by('-created_at')[:6]
    
    # 인기 테스트 가져오기 (심리 테스트와 얼굴상 테스트 통합하여 조회수 기준)
    # 먼저 각 테스트 타입별로 가져온 후 결합
    popular_psycho_tests = Test.objects.all().order_by('-view_count')[:10]
    popular_face_tests = FaceTestModel.objects.filter(is_active=True).order_by('-view_count')[:10]
    
    # 통합 인기 테스트 리스트 생성 (각 테스트에 유형 정보 추가)
    combined_popular = []
    
    for test in popular_psycho_tests:
        combined_popular.append({
            'id': test.id,
            'title': test.title,
            'image': test.image,
            'view_count': test.view_count,
            'type': 'psycho',
            'obj': test
        })
    
    for test in popular_face_tests:
        combined_popular.append({
            'id': test.id,
            'title': test.name,
            'image': test.image,
            'view_count': test.view_count,
            'type': 'face',
            'obj': test
        })
    
    # 조회수 기준 정렬 후 상위 6개 선택
    popular_tests = sorted(combined_popular, key=lambda x: x['view_count'], reverse=True)[:6]
    
    # 커뮤니티 최신 게시글 5개 가져오기
    recent_posts = Post.objects.select_related('category', 'author').order_by('-created_at')[:5]
    
    context = {
        'banners': banners,  # 배너 추가
        'recent_tests': recent_tests,
        'recent_face_tests': recent_face_tests,
        'popular_tests': popular_tests,
        'recent_posts': recent_posts,
    }
    
    return render(request, 'root.html', context)

def inquiry(request):
    """광고 및 협업 문의 페이지"""
    if request.method == 'POST':
        # 폼 데이터 받기
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        subject = request.POST.get('subject', '')
        content = request.POST.get('content', '')
        
        # 필수 필드 검증
        if not all([name, email, subject, content]):
            messages.error(request, '모든 필수 항목을 입력해주세요.')
            return render(request, 'core/inquiry.html', {
                'name': name,
                'email': email,
                'subject': subject,
                'content': content,
            })
        
        # 이메일 전송
        email_subject = f'[새롱] 광고 및 협업 문의: {subject}'
        email_message = f"""
        새롱 사이트에서 새로운 문의가 접수되었습니다.
        
        성함: {name}
        이메일: {email}
        문의제목: {subject}
        
        문의내용:
        {content}
        """
        
        recipient_email = 'farmhoney1298@naver.com'  # 여기에 실제 이메일 주소를 입력하세요
        
        try:
            send_mail(
                email_subject,
                email_message,
                'farmhoney1298@naver.com',  # 발신자 이메일은 네이버 계정과 일치해야 함
                [recipient_email],
                fail_silently=False,
            )
            messages.success(request, '문의가 성공적으로 전송되었습니다. 빠른 시일 내에 답변 드리겠습니다.')
            return redirect('core:inquiry')
        except Exception as e:
            messages.error(request, f'문의 전송 중 오류가 발생했습니다. 다시 시도해주세요. 오류: {str(e)}')
    
    return render(request, 'core/inquiry.html')

@require_GET
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /static/",
        "Disallow: /media/temp/",
        "",
        "Sitemap: https://saerong.com/sitemap.xml"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

def ads_txt(request):
    """Google AdSense ads.txt 파일 제공"""
    content = "google.com, pub-7308084694640774, DIRECT, f08c47fec0942fa0"
    return HttpResponse(content, content_type="text/plain")