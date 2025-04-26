from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
import json
from datetime import datetime, timedelta

# psychotest 앱과 facetest 앱의 모델 가져오기
from psychotest.models import Test as PsychoTest, SharedTestResult

# FaceTestModel 직접 임포트 (try-except 블록 제거)
from facetest.models import FaceTestModel
HAS_FACETEST = True

try:
    # community 앱이 있는 경우 
    from community.models import Post
    HAS_COMMUNITY = True
except ImportError:
    # community 앱이 없는 경우 임시 클래스 생성
    HAS_COMMUNITY = False

@staff_member_required
def admin_views_stats(request):
    """관리자 대시보드에서 조회수 통계를 보여주는 뷰"""
    context = {
        'title': '조회수 분석',
        # 기본값은 마지막 30일
        'start_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
    }
    return render(request, 'analytics/views_stats.html', context)

@staff_member_required
def api_views_data(request):
    """차트에 표시할 데이터를 JSON 형식으로 반환하는 API"""
    # 요청에서 기간 및 집계 유형 가져오기
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    group_by = request.GET.get('group_by', 'day')  # day, week, month
    content_type = request.GET.get('content_type', 'all')  # all, psycho, face, post
    
    # 날짜 파싱
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            start_date = datetime.now() - timedelta(days=30)
            
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        else:
            end_date = datetime.now()
            
        # end_date는 해당 날짜의 23:59:59까지 포함
        end_date = end_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        return JsonResponse({'error': '날짜 형식이 올바르지 않습니다.'}, status=400)
    
    # 집계 함수 선택
    if group_by == 'week':
        trunc_func = TruncWeek
        date_format = '%Y-%m-%d'  # 주의 시작 날짜
    elif group_by == 'month':
        trunc_func = TruncMonth
        date_format = '%Y-%m'
    else:  # day
        trunc_func = TruncDate
        date_format = '%Y-%m-%d'
    
    # 데이터 수집
    data = {
        'labels': [],
        'datasets': []
    }
    
    # 심리 테스트 조회수 데이터
    if content_type in ['all', 'psycho']:
        psycho_data = get_psycho_test_views(start_date, end_date, trunc_func, date_format, group_by)
        data['datasets'].append({
            'label': '심리 테스트',
            'backgroundColor': 'rgba(75, 192, 192, 0.5)',
            'borderColor': 'rgba(75, 192, 192, 1)',
            'borderWidth': 1,
            'data': psycho_data['data'],
        })
        
        # 라벨이 아직 없으면 심리 테스트의 라벨을 사용
        if not data['labels']:
            data['labels'] = psycho_data['labels']
    
    # 얼굴상 테스트 조회수 데이터
    if content_type in ['all', 'face'] and HAS_FACETEST:
        face_data = get_face_test_views(start_date, end_date, trunc_func, date_format, group_by)
        data['datasets'].append({
            'label': '얼굴상 테스트',
            'backgroundColor': 'rgba(153, 102, 255, 0.5)',
            'borderColor': 'rgba(153, 102, 255, 1)',
            'borderWidth': 1,
            'data': face_data['data'],
        })
        
        # 라벨이 아직 없으면 얼굴상 테스트의 라벨을 사용
        if not data['labels']:
            data['labels'] = face_data['labels']
    
    # 커뮤니티 게시글 조회수 데이터
    if content_type in ['all', 'post'] and HAS_COMMUNITY:
        post_data = get_post_views(start_date, end_date, trunc_func, date_format, group_by)
        data['datasets'].append({
            'label': '커뮤니티 게시글',
            'backgroundColor': 'rgba(255, 159, 64, 0.5)',
            'borderColor': 'rgba(255, 159, 64, 1)',
            'borderWidth': 1,
            'data': post_data['data'],
        })
        
        # 라벨이 아직 없으면 게시글의 라벨을 사용
        if not data['labels']:
            data['labels'] = post_data['labels']
    
    # 상위 콘텐츠 가져오기
    top_items = get_top_content(content_type)
    
    return JsonResponse({
        'chart_data': data,
        'top_items': top_items
    })

def get_psycho_test_views(start_date, end_date, trunc_func, date_format, group_by):
    """심리 테스트 조회수 데이터 가져오기"""
    try:
        # 날짜별 조회수 합계 구하기
        views_by_date = (
            PsychoTest.objects
            .filter(created_at__gte=start_date, created_at__lte=end_date)
            .annotate(date=trunc_func('created_at'))
            .values('date')
            .annotate(total_views=Sum('view_count'))
            .order_by('date')
        )
        
        # 데이터 포맷팅
        labels = []
        data = []
        
        for item in views_by_date:
            if group_by == 'month':
                label = item['date'].strftime('%Y-%m')
            else:  # day 또는 week
                label = item['date'].strftime('%Y-%m-%d')
            
            labels.append(label)
            data.append(item['total_views'])
        
        return {'labels': labels, 'data': data}
    except Exception as e:
        print(f"심리 테스트 데이터 가져오기 오류: {str(e)}")
        return {'labels': [], 'data': []}

def get_face_test_views(start_date, end_date, trunc_func, date_format, group_by):
    """얼굴상 테스트 조회수 데이터 가져오기"""
    if not HAS_FACETEST:
        return {'labels': [], 'data': []}
    
    try:
        # 모든 활성화된 얼굴상 테스트의 조회수 가져오기
        total_views = FaceTestModel.objects.filter(is_active=True).aggregate(Sum('view_count'))['view_count__sum'] or 0
        
        # 날짜 범위 생성
        current_date = start_date.date()
        end_date_only = end_date.date()
        date_range = []
        
        while current_date <= end_date_only:
            date_range.append(current_date)
            current_date += timedelta(days=1)
        
        # 날짜별로 조회수 균등 분배
        aggregated_data = {}
        daily_views = total_views / len(date_range) if date_range else 0
        
        for date in date_range:
            if group_by == 'month':
                key = date.strftime('%Y-%m')
            elif group_by == 'week':
                # 주의 시작일로 포맷팅 (월요일 기준)
                week_start = date - timedelta(days=date.weekday())
                key = week_start.strftime('%Y-%m-%d')
            else:  # day
                key = date.strftime('%Y-%m-%d')
            
            if key not in aggregated_data:
                aggregated_data[key] = 0
            
            aggregated_data[key] += daily_views
        
        # 결과 포맷팅
        labels = sorted(aggregated_data.keys())
        data = [round(aggregated_data[key]) for key in labels]
        
        return {'labels': labels, 'data': data}
    except Exception as e:
        print(f"얼굴상 테스트 데이터 가져오기 오류: {str(e)}")
        return {'labels': [], 'data': []}

def get_post_views(start_date, end_date, trunc_func, date_format, group_by):
    """커뮤니티 게시글 조회수 데이터 가져오기"""
    if not HAS_COMMUNITY:
        return {'labels': [], 'data': []}
    
    try:
        # 날짜별 조회수 합계 구하기
        views_by_date = (
            Post.objects
            .filter(created_at__gte=start_date, created_at__lte=end_date)
            .annotate(date=trunc_func('created_at'))
            .values('date')
            .annotate(total_views=Sum('view_count'))
            .order_by('date')
        )
        
        # 데이터 포맷팅
        labels = []
        data = []
        
        for item in views_by_date:
            if group_by == 'month':
                label = item['date'].strftime('%Y-%m')
            else:  # day 또는 week
                label = item['date'].strftime('%Y-%m-%d')
            
            labels.append(label)
            data.append(item['total_views'])
        
        return {'labels': labels, 'data': data}
    except Exception as e:
        print(f"커뮤니티 게시글 데이터 가져오기 오류: {str(e)}")
        return {'labels': [], 'data': []}

def get_top_content(content_type, limit=10):
    """상위 조회수 콘텐츠 가져오기"""
    result = []
    
    # 심리 테스트 상위 항목
    if content_type in ['all', 'psycho']:
        try:
            top_psycho = PsychoTest.objects.order_by('-view_count')[:limit]
            for item in top_psycho:
                result.append({
                    'type': 'psycho',
                    'id': item.id,
                    'title': item.title,
                    'views': item.view_count,
                    'url': f'/admin/psychotest/test/{item.id}/change/'
                })
        except Exception as e:
            print(f"상위 심리 테스트 가져오기 오류: {str(e)}")
    
    # 얼굴상 테스트 상위 항목
    if content_type in ['all', 'face'] and HAS_FACETEST:
        try:
            top_face = FaceTestModel.objects.filter(is_active=True).order_by('-view_count')[:limit]
            for item in top_face:
                result.append({
                    'type': 'face',
                    'id': item.id,
                    'title': item.name,
                    'views': item.view_count,
                    'url': f'/admin/facetest/facetestmodel/{item.id}/change/'
                })
        except Exception as e:
            print(f"상위 얼굴상 테스트 가져오기 오류: {str(e)}")
    
    # 커뮤니티 게시글 상위 항목
    if content_type in ['all', 'post'] and HAS_COMMUNITY:
        try:
            top_posts = Post.objects.order_by('-view_count')[:limit]
            for item in top_posts:
                result.append({
                    'type': 'post',
                    'id': item.id,
                    'title': item.title,
                    'views': item.view_count,
                    'url': f'/admin/community/post/{item.id}/change/'
                })
        except Exception as e:
            print(f"상위 게시글 가져오기 오류: {str(e)}")
    
    # 모든 콘텐츠 중에서 조회수 기준 상위 항목 선택
    result.sort(key=lambda x: x['views'], reverse=True)
    return result[:limit]

@staff_member_required
def content_stats(request, app_name):
    """특정 앱의 콘텐츠별 조회수 통계를 보여주는 뷰"""
    app_labels = {
        'psycho': '심리 테스트',
        'face': '얼굴상 테스트',
        'post': '커뮤니티 게시글'
    }
    
    app_label = app_labels.get(app_name, app_name)
    
    context = {
        'title': f'{app_label} 콘텐츠 조회수 분석',
        'app_name': app_name,
        'app_label': app_label,
        'start_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        'end_date': datetime.now().strftime('%Y-%m-%d'),
    }
    return render(request, 'analytics/content_stats.html', context)

@staff_member_required
def api_content_data(request, app_name):
    """특정 앱의 콘텐츠별 조회수 데이터를 JSON 형식으로 반환하는 API"""
    # 요청에서 기간 및 집계 유형 가져오기
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    limit = int(request.GET.get('limit', '10'))
    
    # 날짜 파싱
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            start_date = datetime.now() - timedelta(days=30)
            
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        else:
            end_date = datetime.now()
            
        # end_date는 해당 날짜의 23:59:59까지 포함
        end_date = end_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        return JsonResponse({'error': '날짜 형식이 올바르지 않습니다.'}, status=400)
    
    # 앱에 따라 데이터 가져오기
    if app_name == 'psycho':
        content_data = get_psycho_content_data(limit)
    elif app_name == 'face' and HAS_FACETEST:
        content_data = get_face_content_data(limit)
    elif app_name == 'post' and HAS_COMMUNITY:
        content_data = get_post_content_data(limit)
    else:
        content_data = []
    
    return JsonResponse({
        'content_data': content_data,
    })

def get_psycho_content_data(limit=10):
    """심리 테스트의 콘텐츠별 조회수 데이터 가져오기"""
    try:
        # 테스트 목록 가져오기
        tests = PsychoTest.objects.order_by('-view_count')[:limit]
        
        # 데이터 포맷팅
        data = []
        for test in tests:
            data.append({
                'id': test.id,
                'title': test.title,
                'views': test.view_count,
                'url': f'/admin/psychotest/test/{test.id}/change/',
                'created_at': test.created_at.strftime('%Y-%m-%d')
            })
        
        return data
    except Exception as e:
        print(f"심리 테스트 콘텐츠 데이터 가져오기 오류: {str(e)}")
        return []

def get_face_content_data(limit=10):
    """얼굴상 테스트의 콘텐츠별 조회수 데이터 가져오기"""
    try:
        # 테스트 목록 가져오기
        tests = FaceTestModel.objects.filter(is_active=True).order_by('-view_count')[:limit]
        
        # 데이터 포맷팅
        data = []
        for test in tests:
            data.append({
                'id': test.id,
                'title': test.name,
                'views': test.view_count,
                'url': f'/admin/facetest/facetestmodel/{test.id}/change/',
                'created_at': test.created_at.strftime('%Y-%m-%d')
            })
        
        return data
    except Exception as e:
        print(f"얼굴상 테스트 콘텐츠 데이터 가져오기 오류: {str(e)}")
        return []

def get_post_content_data(limit=10):
    """커뮤니티 게시글의 콘텐츠별 조회수 데이터 가져오기"""
    try:
        # 게시글 목록 가져오기
        posts = Post.objects.order_by('-view_count')[:limit]
        
        # 데이터 포맷팅
        data = []
        for post in posts:
            data.append({
                'id': post.id,
                'title': post.title,
                'views': post.view_count,
                'url': f'/admin/community/post/{post.id}/change/',
                'created_at': post.created_at.strftime('%Y-%m-%d'),
                'category': post.category.name if post.category else '-'
            })
        
        return data
    except Exception as e:
        print(f"커뮤니티 게시글 콘텐츠 데이터 가져오기 오류: {str(e)}")
        return []