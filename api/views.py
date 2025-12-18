import base64
import json
import requests
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django_filters.rest_framework import DjangoFilterBackend
from core.models import Category, SubCategory
from sources.models import DataSource
from collector.models import CollectedData, CrawlLog
from .models import Game, GameCategory, Subscription, PushToken, UserProfile, CarrotBalance, CarrotTransaction
from .serializers import (
    CategorySerializer,
    SubCategorySerializer,
    DataSourceSerializer,
    CollectedDataSerializer,
    CollectedDataListSerializer,
    CrawlLogSerializer,
    GameSerializer,
    SubscriptionSerializer,
    SubscriptionCreateSerializer,
    PushTokenSerializer,
    NotificationSerializer
)
from .permissions import IsAdminUserWithMessage


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """카테고리 API ViewSet (읽기 전용)"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    lookup_field = 'slug'

    @action(detail=True, methods=['get'])
    def subcategories(self, request, slug=None):
        """특정 카테고리의 서브카테고리 목록"""
        category = self.get_object()
        subcategories = category.subcategories.filter(is_active=True)
        serializer = SubCategorySerializer(subcategories, many=True)
        return Response(serializer.data)


class SubCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """서브카테고리 API ViewSet (읽기 전용)"""
    queryset = SubCategory.objects.filter(is_active=True)
    serializer_class = SubCategorySerializer
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']

    @action(detail=True, methods=['get'])
    def sources(self, request, slug=None):
        """특정 서브카테고리의 데이터 소스 목록"""
        subcategory = self.get_object()
        sources = subcategory.sources.filter(is_active=True)
        serializer = DataSourceSerializer(sources, many=True)
        return Response(serializer.data)


class DataSourceViewSet(viewsets.ReadOnlyModelViewSet):
    """데이터 소스 API ViewSet (읽기 전용)"""
    queryset = DataSource.objects.filter(is_active=True)
    serializer_class = DataSourceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['subcategory', 'crawler_type', 'is_active']
    search_fields = ['name', 'url']

    @action(detail=True, methods=['get'])
    def collected_data(self, request, pk=None):
        """특정 데이터 소스의 수집된 데이터"""
        source = self.get_object()
        data = source.collected_data.all()[:100]  # 최근 100개
        serializer = CollectedDataListSerializer(data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """특정 데이터 소스의 크롤링 로그"""
        source = self.get_object()
        logs = source.crawl_logs.all()[:50]  # 최근 50개
        serializer = CrawlLogSerializer(logs, many=True)
        return Response(serializer.data)


class CollectedDataViewSet(viewsets.ReadOnlyModelViewSet):
    """수집된 데이터 API ViewSet (읽기 전용)"""
    queryset = CollectedData.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['source', 'source__subcategory', 'source__subcategory__category']
    search_fields = ['data']
    ordering_fields = ['collected_at']
    ordering = ['-collected_at']

    def get_serializer_class(self):
        """목록 조회 시 간소화된 serializer 사용"""
        if self.action == 'list':
            return CollectedDataListSerializer
        return CollectedDataSerializer

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """최신 수집 데이터 (기본 20개)"""
        limit = int(request.query_params.get('limit', 20))
        data = self.get_queryset()[:limit]
        serializer = CollectedDataListSerializer(data, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_game(self, request):
        """게임별로 그룹화된 최신 데이터"""
        game_name = request.query_params.get('game', '메이플스토리')
        limit = int(request.query_params.get('limit', 20))

        # data 필드의 JSON에서 game 필드로 필터링
        data = CollectedData.objects.filter(
            data__game=game_name
        ).order_by('-collected_at')[:limit]

        serializer = CollectedDataListSerializer(data, many=True)
        return Response(serializer.data)


class CrawlLogViewSet(viewsets.ReadOnlyModelViewSet):
    """크롤링 로그 API ViewSet (읽기 전용)"""
    queryset = CrawlLog.objects.all()
    serializer_class = CrawlLogSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['source', 'status']
    ordering_fields = ['started_at', 'completed_at', 'duration_seconds']
    ordering = ['-started_at']

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """크롤링 통계"""
        from django.db.models import Count, Avg, Sum

        total_logs = self.get_queryset().count()
        success_logs = self.get_queryset().filter(status='success').count()
        failed_logs = self.get_queryset().filter(status='failed').count()

        avg_duration = self.get_queryset().aggregate(
            avg=Avg('duration_seconds')
        )['avg'] or 0

        total_items = self.get_queryset().aggregate(
            total=Sum('items_collected')
        )['total'] or 0

        return Response({
            'total_crawls': total_logs,
            'successful_crawls': success_logs,
            'failed_crawls': failed_logs,
            'success_rate': f"{(success_logs / total_logs * 100):.1f}%" if total_logs > 0 else "0%",
            'average_duration_seconds': round(avg_duration, 2),
            'total_items_collected': total_items,
        })


@api_view(['GET'])
def subcategory_data_api(request, slug):
    """
    중분류(SubCategory) 데이터 API
    각 소분류(DataSource)별로 최신 10개 데이터 반환
    모바일 앱 알림용
    """
    subcategory = get_object_or_404(SubCategory, slug=slug, is_active=True)

    # 활성화된 데이터 소스들 가져오기
    data_sources = subcategory.data_sources.filter(is_active=True).order_by('name')

    # 각 데이터 소스별로 최신 10개 데이터 수집
    result_data = {}
    for source in data_sources:
        items = CollectedData.objects.filter(
            source=source
        ).order_by('-collected_at')[:10]

        # 데이터 포맷팅 (title, url, date, collected_at만 추출)
        formatted_items = []
        for item in items:
            formatted_item = {
                'title': item.data.get('title', ''),
                'url': item.data.get('url', ''),
                'date': item.data.get('date', ''),
                'collected_at': item.collected_at.isoformat(),
            }
            formatted_items.append(formatted_item)

        result_data[source.name] = formatted_items

    response_data = {
        'subcategory': subcategory.name,
        'category': subcategory.category.name,
        'updated_at': CollectedData.objects.filter(
            source__subcategory=subcategory
        ).order_by('-collected_at').first().collected_at.isoformat() if CollectedData.objects.filter(
            source__subcategory=subcategory
        ).exists() else None,
        'data': result_data
    }

    return Response(response_data)


# ============================================
# Game Honey API Views
# ============================================

class GameViewSet(viewsets.ReadOnlyModelViewSet):
    """게임 목록 API"""
    queryset = Game.objects.filter(is_active=True)
    serializer_class = GameSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'game_id'


class SubscriptionViewSet(viewsets.ModelViewSet):
    """구독 관리 API"""
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """현재 사용자의 구독 목록만 반환"""
        return Subscription.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """생성 시에는 SubscriptionCreateSerializer 사용"""
        if self.action == 'create':
            return SubscriptionCreateSerializer
        return SubscriptionSerializer

    def create(self, request, *args, **kwargs):
        """구독 생성 (등급 제한 적용)"""
        from django.utils import timezone

        # 1. 중복 구독 체크 (이미 구독 중이면 바로 반환)
        game_id = request.data.get('game_id')
        category = request.data.get('category')

        if game_id and category:
            try:
                game = Game.objects.get(game_id=game_id)
                existing = Subscription.objects.filter(
                    user=request.user,
                    game=game,
                    category=category
                ).first()

                if existing:
                    # 이미 구독 중이면 200 OK로 반환
                    serializer = SubscriptionSerializer(existing)
                    return Response(serializer.data, status=status.HTTP_200_OK)
            except Game.DoesNotExist:
                pass  # 게임이 없으면 나중에 Serializer에서 에러 발생

        # 2. 활성 구독권 확인
        try:
            premium = PremiumSubscription.objects.get(user=request.user)
            if not premium.is_active:
                # 만료된 구독권 삭제
                premium.delete()
                raise PremiumSubscription.DoesNotExist
        except PremiumSubscription.DoesNotExist:
            return Response(
                {'error': '구독하려면 광고를 시청하거나 프리미엄을 구매해주세요.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 3. 광고 구독자 제한 확인 (1개 게임만, 같은 게임 내 다른 카테고리는 허용)
        if premium.subscription_type == 'free_ad':
            # 현재 구독하려는 게임
            try:
                game = Game.objects.get(game_id=game_id)
                already_subscribed_to_this_game = Subscription.objects.filter(
                    user=request.user, game=game
                ).exists()
            except Game.DoesNotExist:
                already_subscribed_to_this_game = False

            # 이미 이 게임을 구독 중이면 다른 카테고리 추가 허용
            if not already_subscribed_to_this_game:
                # 새로운 게임을 구독하려는 경우에만 제한 확인
                current_game_count = Subscription.objects.filter(user=request.user).values('game').distinct().count()
                if current_game_count >= 1:
                    return Response(
                        {'error': '광고 구독은 1개 게임만 구독할 수 있습니다. 프리미엄을 구매하면 무제한으로 구독할 수 있어요.'},
                        status=status.HTTP_403_FORBIDDEN
                    )

        # 4. 구독 생성
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """구독 생성 시 user 자동 설정"""
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """구독 취소"""
        subscription = self.get_object()

        # 본인의 구독인지 확인 (get_queryset에서 이미 필터링되지만 재확인)
        if subscription.user != request.user:
            return Response(
                {'error': '권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        subscription.delete()
        return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)


class PushTokenViewSet(viewsets.ModelViewSet):
    """푸시 토큰 관리 API"""
    serializer_class = PushTokenSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']  # PUT/PATCH 제외

    def get_queryset(self):
        """현재 사용자의 푸시 토큰만 반환"""
        return PushToken.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """푸시 토큰 등록/업데이트"""
        token = request.data.get('token')
        device_type = request.data.get('device_type', 'android')

        if not token:
            return Response(
                {'error': 'token이 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 기존 토큰이 있으면 업데이트, 없으면 생성
        push_token, created = PushToken.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'device_type': device_type
            }
        )

        serializer = self.get_serializer(push_token)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_feed(request):
    """
    알림 피드 API
    현재 사용자가 구독한 게임+카테고리의 최신 소식 반환
    """
    # 사용자의 구독 목록 조회
    subscriptions = Subscription.objects.filter(user=request.user).select_related('game')

    # 구독한 게임+카테고리의 최신 데이터 수집
    notifications = []

    for sub in subscriptions:
        # 해당 게임의 SubCategory 찾기
        try:
            subcategory = SubCategory.objects.get(
                name__icontains=sub.game.display_name,
                is_active=True
            )
        except (SubCategory.DoesNotExist, SubCategory.MultipleObjectsReturned):
            continue

        # 해당 카테고리의 DataSource 찾기
        data_sources = subcategory.data_sources.filter(
            name__icontains=sub.category,
            is_active=True
        )

        for source in data_sources:
            # 최신 데이터 10개 가져오기
            items = CollectedData.objects.filter(
                source=source
            ).order_by('-collected_at')[:10]

            for item in items:
                notifications.append({
                    'game': sub.game.display_name,
                    'game_id': sub.game.game_id,
                    'category': sub.category,
                    'title': item.data.get('title', ''),
                    'url': item.data.get('url', ''),
                    'date': item.data.get('date', ''),
                    'collected_at': item.collected_at
                })

    # 최신순 정렬
    notifications.sort(key=lambda x: x['collected_at'], reverse=True)

    # 페이지네이션 (선택적)
    limit = int(request.query_params.get('limit', 50))
    notifications = notifications[:limit]

    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


# ============================================
# Toss Disconnect Callback
# ============================================

def verify_basic_auth(request, app=None):
    """
    Basic Auth 검증

    Args:
        request: HTTP request
        app: TossApp 객체 (None이면 settings 사용)
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    if not auth_header.startswith('Basic '):
        return False

    try:
        # "Basic " 제거하고 base64 디코딩
        encoded_credentials = auth_header[6:]
        decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
        username, password = decoded_credentials.split(':', 1)

        # 앱별 설정 또는 레거시 settings
        if app and app.disconnect_callback_username:
            expected_username = app.disconnect_callback_username
            expected_password = app.disconnect_callback_password
        else:
            expected_username = settings.TOSS_DISCONNECT_CALLBACK_USERNAME
            expected_password = settings.TOSS_DISCONNECT_CALLBACK_PASSWORD

        return username == expected_username and password == expected_password
    except Exception as e:
        print(f"Basic Auth verification failed: {e}")
        return False


@csrf_exempt
def toss_disconnect_callback(request, app_id=None):
    """
    토스 연결 끊기 콜백 (Django 기본 뷰 - 모든 Content-Type 지원)

    사용자가 토스앱에서 앱 연결을 끊거나 회원 탈퇴할 때 호출됨
    """
    # common 모듈 import (없으면 None)
    try:
        from common.models import AppUserToken
    except ImportError:
        AppUserToken = None

    # 0. 앱 설정 조회
    try:
        app = get_toss_app(app_id) if app_id else get_toss_app(DEFAULT_APP_ID)
    except (ValueError, Exception):
        app = None  # 레거시 모드

    # 1. Basic Auth 검증
    if not verify_basic_auth(request, app):
        return JsonResponse(
            {
                'resultType': 'FAIL',
                'error': {
                    'reason': 'UNAUTHORIZED',
                    'message': 'Invalid Basic Auth credentials'
                }
            },
            status=401
        )

    # 2. 요청 본문 파싱 (JSON 우선, form-data 폴백)
    data = {}
    try:
        # 먼저 JSON 파싱 시도 (Content-Type 무관하게)
        if request.body:
            data = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        # JSON 파싱 실패 시 form-data 시도
        try:
            data = dict(request.POST)
            data = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in data.items()}
        except Exception as e:
            print(f"Failed to parse request body: {e}")
            data = {}

    # userKey 추출 (camelCase와 snake_case 모두 지원)
    # 주의: userKey가 0일 수 있으므로 None 체크만 해야 함
    user_key = data.get('userKey')
    if user_key is None:
        user_key = data.get('user_key')
    if user_key is None:
        print(f"Disconnect callback - missing userKey. data: {data}, body: {request.body[:200]}")
        return JsonResponse(
            {
                'resultType': 'FAIL',
                'error': {
                    'reason': 'INVALID_REQUEST',
                    'message': 'userKey is required'
                }
            },
            status=400
        )

    # 3. referrer 로깅 (연결 해제 사유)
    referrer = data.get('referrer', 'UNKNOWN')
    print(f"Disconnect callback: userKey={user_key}, referrer={referrer}")

    try:
        # 4. 사용자 찾기 (UserProfile을 통해)
        profile = UserProfile.objects.get(toss_user_key=user_key)
        user = profile.user

        # 5. 트랜잭션으로 데이터 삭제
        with transaction.atomic():
            if app and AppUserToken:
                # 앱별 토큰만 삭제 (멀티 앱 모드)
                AppUserToken.objects.filter(user=user, app=app).delete()
                print(f"User {user_key} disconnected from app '{app.app_id}'")

                # 다른 앱 토큰이 없으면 profile도 초기화 (토스 연결 완전 해제)
                remaining_tokens = AppUserToken.objects.filter(user=user).count()
                if remaining_tokens == 0:
                    # 모든 앱에서 연결 해제됨 - profile 초기화
                    profile.toss_user_key = None
                    profile.toss_access_token = ''
                    profile.toss_refresh_token = ''
                    profile.save()
                    print(f"User {user_key} - all app tokens deleted, profile reset")

                # 해당 앱이 game_honey면 게임 관련 데이터도 삭제
                if app.app_id == 'game_honey':
                    user.game_subscriptions.all().delete()
                    user.push_tokens.all().delete()
                    if hasattr(user, 'premium_subscription'):
                        user.premium_subscription.delete()
                    print(f"User {user_key} - game_honey data deleted")
            else:
                # 레거시 모드: 토스 연결 해제 (사용자 데이터 보존)
                profile.toss_user_key = None
                profile.toss_access_token = ''
                profile.toss_refresh_token = ''
                profile.save()

                # 프리미엄 구독도 취소
                if hasattr(user, 'premium_subscription'):
                    user.premium_subscription.delete()

                # 게임 구독 삭제
                user.game_subscriptions.all().delete()

                print(f"User {user_key} disconnected (legacy mode) - profile preserved")

        # 6. 성공 응답
        return JsonResponse({
            'resultType': 'SUCCESS',
            'success': {'userKey': user_key}
        })

    except UserProfile.DoesNotExist:
        # 사용자가 존재하지 않아도 SUCCESS 반환
        print(f"User {user_key} not found, but returning success")
        return JsonResponse({
            'resultType': 'SUCCESS',
            'success': {'userKey': user_key}
        })

    except Exception as e:
        print(f"Error in toss_disconnect_callback: {e}")
        return JsonResponse(
            {
                'resultType': 'FAIL',
                'error': {
                    'reason': 'INTERNAL_ERROR',
                    'message': str(e)
                }
            },
            status=500
        )


# ============================================
# Toss Login API
# ============================================

from api.toss_auth import (
    get_toss_app,
    get_toss_access_token,
    refresh_toss_access_token,
    get_toss_user_info,
    get_or_create_user_from_toss,
    create_jwt_token,
    get_user_from_token,
    save_app_user_token,
    DEFAULT_APP_ID,
)


@api_view(['POST'])
@permission_classes([AllowAny])
def toss_login(request):
    """
    토스 로그인 API

    앱에서 appLogin()으로 받은 authorizationCode를 전송하면
    JWT 토큰을 발급합니다.

    멀티 앱 지원:
    - app_id를 전송하면 해당 앱의 Toss 설정 사용
    - app_id가 없으면 'game_honey'를 기본값으로 사용 (하위 호환)

    Request:
        {
            "appId": "game_honey",  // 선택 (기본값: game_honey)
            "authorizationCode": "abc123...",
            "referrer": "DEFAULT" | "SANDBOX"
        }

    Response:
        {
            "access_token": "eyJ...",
            "refresh_token": "eyJ...",
            "user": {
                "id": 1,
                "username": "toss_443731104",
                "toss_user_key": 443731104
            }
        }
    """
    # CamelCaseJSONParser가 authorizationCode를 authorization_code로 변환함
    app_id = request.data.get('app_id', DEFAULT_APP_ID)  # 기본값: game_honey
    authorization_code = request.data.get('authorization_code')
    referrer = request.data.get('referrer', 'DEFAULT')

    if not authorization_code:
        return Response(
            {'error': 'authorization_code is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # 0. 앱 설정 조회 (없으면 레거시 모드)
        app = get_toss_app(app_id)

        # 1. 토스 API에서 AccessToken 발급
        toss_token_data = get_toss_access_token(authorization_code, referrer, app)
        toss_access_token = toss_token_data['accessToken']
        toss_refresh_token = toss_token_data['refreshToken']

        # 2. 토스 API에서 사용자 정보 조회
        toss_user_info = get_toss_user_info(toss_access_token, app)
        user_key = toss_user_info['userKey']

        # 3. 사용자 찾기 또는 생성
        user, created = get_or_create_user_from_toss(user_key, toss_user_info, app)

        # 4. 토스 토큰 저장 (앱별로 저장)
        save_app_user_token(user, app, toss_access_token, toss_refresh_token)

        # 5. refrigeratorchef 앱 첫 로그인 시 당근 20개 지급
        welcome_carrots = 0
        if app_id == 'refrigeratorchef':
            from api.models import CarrotBalance
            balance, balance_created = CarrotBalance.objects.get_or_create(user=user)
            if balance_created:
                # 첫 CarrotBalance 생성 = 첫 로그인
                balance.add_carrots(20, 'welcome_bonus')
                welcome_carrots = 20

        # 6. JWT 토큰 발급 (우리 서버용)
        access_token = create_jwt_token(user.id, 'access')
        refresh_token = create_jwt_token(user.id, 'refresh')

        # 7. 응답
        return Response({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'toss_user_key': user_key,
                'name': user.first_name,
                'is_new': created
            },
            'welcomeCarrots': welcome_carrots  # 첫 로그인 시 지급된 당근 (0이면 기존 회원)
        }, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        print(f"Error in toss_login: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    JWT 토큰 갱신 API

    Request:
        {
            "refreshToken": "eyJ..."  (camelCase 권장)
            또는 "refresh_token": "eyJ..."  (snake_case 호환)
        }

    Response:
        {
            "accessToken": "eyJ...(새로운 액세스 토큰)",
            "refreshToken": "eyJ...(새로운 리프레시 토큰)"
        }
    """
    # camelCase와 snake_case 모두 지원
    token = request.data.get('refreshToken') or request.data.get('refresh_token')

    if not token:
        return Response(
            {'error': 'refreshToken is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # JWT 토큰에서 사용자 찾기
        user = get_user_from_token(token)

        if not user:
            return Response(
                {'error': 'Invalid refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 새 AccessToken 및 RefreshToken 발급
        new_access_token = create_jwt_token(user.id, 'access')
        new_refresh_token = create_jwt_token(user.id, 'refresh')

        return Response({
            'accessToken': new_access_token,
            'refreshToken': new_refresh_token
        }, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        print(f"Error in refresh_token: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    현재 로그인한 사용자 정보 조회 API

    Header:
        Authorization: Bearer <jwt_token>

    Response (200):
        {
            "id": 1,
            "username": "toss_443731104",
            "name": "김토스",
            "toss_user_key": 443731104
        }

    Response (401):
        - 토큰 만료/무효: IsAuthenticated에서 자동 처리
        - 토스 연결 해제된 유저: {"error": "Toss account disconnected"}
    """
    try:
        user = request.user

        # 프로필 존재 여부 확인
        if not hasattr(user, 'profile'):
            return Response(
                {'error': 'User profile not found'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        profile = user.profile

        # 토스 연결 해제 여부 확인 (toss_user_key가 None이면 연결 해제됨)
        if profile.toss_user_key is None:
            return Response(
                {'error': 'Toss account disconnected'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response({
            'id': user.id,
            'username': user.username,
            'name': user.first_name or user.username,
            'toss_user_key': profile.toss_user_key
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error in get_current_user: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    로그아웃 API

    Header:
        Authorization: Bearer <jwt_token>

    Response:
        {
            "success": true
        }
    """
    try:
        # 여기서는 JWT 토큰을 무효화하지 않습니다
        # (Stateless JWT의 특성상, 토큰은 만료될 때까지 유효)
        # 필요시 Redis 등을 사용해 블랙리스트 관리 가능

        # 토스 Access Token 삭제 (선택사항)
        # user = request.user
        # user.profile.toss_access_token = ''
        # user.profile.toss_refresh_token = ''
        # user.profile.save()

        return Response({
            'success': True,
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error in logout: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# Premium Subscription API
# ============================================

from .models import PremiumSubscription
from .serializers import PremiumSubscriptionSerializer, PremiumGrantSerializer
from datetime import timedelta


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def premium_status(request):
    """
    프리미엄 구독 상태 조회 API

    GET /api/premium/status/

    Response:
        {
            "isPremium": true,
            "expiresAt": "2025-12-19T00:00:00Z",
            "subscriptionType": "free_ad",
            "maxGames": 1,  // free_ad: 1, premium: null (무제한)
            "subscribedGamesCount": 0,
            "canSubscribeMore": true
        }
    """
    try:
        user = request.user

        # 현재 구독 중인 게임 수 계산
        subscribed_games_count = Subscription.objects.filter(user=user).values('game').distinct().count()

        try:
            subscription = PremiumSubscription.objects.get(user=user)

            # 만료된 구독은 삭제
            if not subscription.is_active:
                # 모든 게임 구독도 함께 삭제
                Subscription.objects.filter(user=user).delete()
                subscription.delete()
                return Response({
                    'is_premium': False,
                    'expires_at': None,
                    'subscription_type': None,
                    'max_games': None,
                    'subscribed_games_count': 0,  # 모두 삭제되었으므로 0
                    'can_subscribe_more': False
                }, status=status.HTTP_200_OK)

            # 구독 유형에 따른 최대 게임 수 설정
            max_games = 1 if subscription.subscription_type == 'free_ad' else None

            # 추가 구독 가능 여부
            if subscription.subscription_type == 'free_ad':
                can_subscribe_more = subscribed_games_count < 1
            else:  # premium
                can_subscribe_more = True

            return Response({
                'is_premium': True,
                'expires_at': subscription.expires_at,
                'subscription_type': subscription.subscription_type,
                'max_games': max_games,
                'subscribed_games_count': subscribed_games_count,
                'can_subscribe_more': can_subscribe_more
            }, status=status.HTTP_200_OK)

        except PremiumSubscription.DoesNotExist:
            return Response({
                'is_premium': False,
                'expires_at': None,
                'subscription_type': None,
                'max_games': None,
                'subscribed_games_count': subscribed_games_count,
                'can_subscribe_more': False
            }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error in premium_status: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def grant_premium(request):
    """
    프리미엄 구독권 부여 API

    POST /api/premium/grant/

    Request:
        {
            "subscriptionType": "free_ad",  // "free_ad" (7일) 또는 "premium" (180일)
            "orderId": "uuid-v7"  // 인앱결제 주문 ID (결제 검증용, optional)
        }

    Response:
        {
            "expiresAt": "2025-12-26T00:00:00Z"
        }
    """
    serializer = PremiumGrantSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = request.user
        subscription_type = serializer.validated_data['subscription_type']
        order_id = serializer.validated_data.get('order_id')

        # premium 구독의 경우 order_id 필수
        if subscription_type == 'premium' and not order_id:
            return Response(
                {'error': 'order_id is required for premium subscription'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # premium 구독의 경우 결제 검증 (TODO: Apps in Toss 결제 검증 API 연동)
        if subscription_type == 'premium' and order_id:
            # TODO: 토스 인앱결제 검증 API 호출
            # https://developers-apps-in-toss.toss.im/iap/develop
            # verified = verify_iap_purchase(order_id)
            # if not verified:
            #     return Response({'error': 'Invalid order'}, status=status.HTTP_400_BAD_REQUEST)
            pass

        # 구독 기간 설정
        from django.utils import timezone
        now = timezone.now()

        if subscription_type == 'free_ad':
            duration = timedelta(days=7)
        else:  # premium
            days = serializer.validated_data.get('days', 180)
            duration = timedelta(days=int(days))

        # 기존 구독이 있으면 업그레이드/갱신, 없으면 새로 생성
        try:
            subscription = PremiumSubscription.objects.get(user=user)

            # 광고 → 프리미엄 전환: 기존 광고 구독 취소하고 새로 시작
            if subscription.subscription_type == 'free_ad' and subscription_type == 'premium':
                subscription.subscription_type = subscription_type
                subscription.expires_at = now + duration
                subscription.order_id = order_id
                subscription.save()

            # 같은 타입 갱신: 만료일 연장
            elif subscription.subscription_type == subscription_type:
                if subscription.is_active:
                    subscription.expires_at = subscription.expires_at + duration
                else:
                    # 만료된 구독이면 현재 시각부터 새로 시작
                    subscription.expires_at = now + duration
                subscription.order_id = order_id
                subscription.save()

            # 프리미엄 → 광고 다운그레이드 방지
            elif subscription.subscription_type == 'premium' and subscription_type == 'free_ad':
                return Response(
                    {'error': '프리미엄 구독 중에는 광고 구독을 사용할 수 없습니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except PremiumSubscription.DoesNotExist:
            # 새 구독 생성
            subscription = PremiumSubscription.objects.create(
                user=user,
                subscription_type=subscription_type,
                expires_at=now + duration,
                order_id=order_id
            )

        return Response({
            'expires_at': subscription.expires_at
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error in grant_premium: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_premium(request):
    """
    프리미엄 구독 취소 API

    POST /api/premium/cancel/

    Response:
        {
            "success": true,
            "message": "구독이 취소되었습니다."
        }
    """
    try:
        user = request.user

        # 프리미엄 구독 찾기
        try:
            subscription = PremiumSubscription.objects.get(user=user)

            # 모든 게임 구독 삭제
            deleted_count = Subscription.objects.filter(user=user).delete()[0]

            # 프리미엄 구독 삭제 (즉시 만료)
            subscription.delete()

            return Response({
                'success': True,
                'message': f'구독이 취소되었습니다. (게임 구독 {deleted_count}개 삭제)',
                'deleted_subscriptions': deleted_count
            }, status=status.HTTP_200_OK)

        except PremiumSubscription.DoesNotExist:
            return Response(
                {'error': '활성 구독이 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        print(f"Error in cancel_premium: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# 테스트 API (개발/디버깅용)
# ============================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_push_notification(request):
    """
    푸시 알림 테스트 API (개발/디버깅용)

    POST /api/test/push/

    Request:
        {
            "title": "테스트 제목",
            "body": "테스트 본문" (optional)
        }

    Response:
        {
            "success": true,
            "message": "푸시 알림 발송 완료",
            "user_key": 123456789,
            "title": "테스트 제목"
        }
    """
    try:
        user = request.user
        title = request.data.get('title', '[테스트] 푸시 알림 테스트')
        body = request.data.get('body', '이것은 테스트 푸시 알림입니다.')

        # 사용자의 toss_user_key 확인
        user_key = None

        # 1. 현재 사용자가 toss_user_key를 가지고 있으면 사용
        if hasattr(user, 'profile') and user.profile.toss_user_key:
            user_key = user.profile.toss_user_key

        # 2. 관리자 사용자인 경우, 자신의 toss_user_key로 테스트
        elif user.is_staff or user.is_superuser:
            # 관리자 본인의 UserProfile에서 toss_user_key 찾기
            try:
                from api.models import UserProfile
                admin_profile = UserProfile.objects.filter(user=user).first()
                if admin_profile and admin_profile.toss_user_key:
                    user_key = admin_profile.toss_user_key
                else:
                    # 관리자도 toss_user_key가 없으면, 첫 번째 활성 사용자로 테스트
                    first_profile = UserProfile.objects.filter(toss_user_key__isnull=False).first()
                    if first_profile:
                        user_key = first_profile.toss_user_key
                        print(f"[Admin Test] Using first available user_key: {user_key}")
                    else:
                        return Response({
                            'error': '테스트할 사용자가 없습니다. 토스 로그인한 사용자가 필요합니다.'
                        }, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                print(f"Error finding test user_key: {e}")
                return Response({
                    'error': f'사용자 조회 실패: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. 일반 사용자인데 toss_user_key가 없으면 에러
        else:
            return Response(
                {'error': '토스 로그인이 필요합니다. (user_key 없음)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 푸시 알림 발송
        from api.push_notifications import send_toss_push_notification

        user_keys = [user_key]
        data = {
            "test": True,
            "url": "https://saerong.com",
            "game_id": "게임 하니",
            "category": "테스트 알림"
        }

        success = send_toss_push_notification(
            user_keys=user_keys,
            title=title,
            body=body,
            data=data
        )

        if success:
            return Response({
                'success': True,
                'message': '푸시 알림 발송 완료',
                'user_key': user_key,
                'title': title,
                'body': body
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': '푸시 알림 발송 실패 (토스 API 에러 또는 인증서 미설정)'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        print(f"Error in test_push_notification: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {'error': f'Internal server error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def api_guide(request):
    """
    Game Honey API 가이드 페이지 (관리자 전용)

    GET /api/guide/
    """
    from django.contrib.auth.models import User

    # 통계 데이터
    games_count = Game.objects.filter(is_active=True).count()
    users_count = User.objects.count()
    subscriptions_count = Subscription.objects.count()

    return render(request, 'api/api_guide.html', {
        'games_count': games_count,
        'users_count': users_count,
        'subscriptions_count': subscriptions_count,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def crawler_status(request):
    """
    크롤러 상태 API

    GET /api/crawler/status/

    Response:
        {
            "is_running": true,
            "current_task": {
                "source_id": 52,
                "source_name": "메이플스토리 공지사항",
                "game_name": "메이플스토리",
                "started_at": "2025-11-26T12:34:56Z"
            },
            "queue_length": 3,
            "queued_sources": ["던파 공지", "리니지 공지", ...],
            "total_sources": 10,
            "last_crawl_results": [
                {
                    "source_name": "메이플스토리 공지사항",
                    "status": "success",
                    "items_collected": 5,
                    "completed_at": "2025-11-26T12:30:00Z"
                },
                ...
            ]
        }
    """
    from saerong.celery import app as celery_app
    from datetime import datetime

    try:
        # 1. Celery에서 활성 태스크 조회
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active() or {}
        reserved_tasks = inspect.reserved() or {}  # 대기 중인 태스크

        current_task = None
        is_running = False
        queue_length = 0
        queued_sources = []

        # 활성 태스크 확인
        for worker, tasks in active_tasks.items():
            for task in tasks:
                if task.get('name') == 'collector.tasks.crawl_data_source':
                    is_running = True
                    source_id = task['args'][0] if task.get('args') else None
                    time_start = task.get('time_start')

                    if source_id:
                        try:
                            source = DataSource.objects.get(id=source_id)
                            current_task = {
                                'source_id': source_id,
                                'source_name': source.name,
                                'game_name': source.subcategory.name if source.subcategory else '',
                                'started_at': datetime.fromtimestamp(time_start).isoformat() if time_start else None
                            }
                        except DataSource.DoesNotExist:
                            current_task = {
                                'source_id': source_id,
                                'source_name': '알 수 없음',
                                'game_name': '',
                                'started_at': datetime.fromtimestamp(time_start).isoformat() if time_start else None
                            }
                    break

        # 대기 중인 태스크 확인
        for worker, tasks in reserved_tasks.items():
            for task in tasks:
                if task.get('name') == 'collector.tasks.crawl_data_source':
                    queue_length += 1
                    source_id = task['args'][0] if task.get('args') else None
                    if source_id:
                        try:
                            source = DataSource.objects.get(id=source_id)
                            queued_sources.append(source.name)
                        except DataSource.DoesNotExist:
                            queued_sources.append(f'소스 #{source_id}')

        # 2. 최근 크롤링 결과 조회
        recent_logs = CrawlLog.objects.select_related('source').order_by('-completed_at')[:10]
        last_crawl_results = []
        for log in recent_logs:
            last_crawl_results.append({
                'source_name': log.source.name if log.source else '알 수 없음',
                'status': log.status,
                'items_collected': log.items_collected,
                'completed_at': log.completed_at.isoformat() if log.completed_at else None,
                'duration_seconds': log.duration_seconds
            })

        # 3. 전체 소스 수
        total_sources = DataSource.objects.filter(is_active=True).count()

        return Response({
            'is_running': is_running,
            'current_task': current_task,
            'queue_length': queue_length,
            'queued_sources': queued_sources[:10],  # 최대 10개만
            'total_sources': total_sources,
            'last_crawl_results': last_crawl_results
        })

    except Exception as e:
        # Celery 연결 실패 등의 경우
        return Response({
            'is_running': False,
            'current_task': None,
            'queue_length': 0,
            'queued_sources': [],
            'total_sources': DataSource.objects.filter(is_active=True).count(),
            'last_crawl_results': [],
            'error': str(e)
        })


# ============================================
# KAMIS API 프록시 (요즘농가용)
# ============================================

from django.core.cache import cache

KAMIS_API_KEY = getattr(settings, 'KAMIS_API_KEY', '')
KAMIS_API_ID = getattr(settings, 'KAMIS_API_ID', 'nowfarm')
KAMIS_CACHE_TIMEOUT = 600  # 10분 캐싱

# 네이버 데이터랩 API (트렌드 모아용)
NAVER_CLIENT_ID = getattr(settings, 'NAVER_CLIENT_ID', '')
NAVER_CLIENT_SECRET = getattr(settings, 'NAVER_CLIENT_SECRET', '')
NAVER_DATALAB_CACHE_TIMEOUT = 3600  # 1시간 캐싱

# OpenAI API (냉장고요리사용)
import openai
import uuid

OPENAI_API_KEY = settings.OPENAI_API_KEY if hasattr(settings, 'OPENAI_API_KEY') else ''


@api_view(['GET'])
@permission_classes([AllowAny])
def kamis_daily_prices(request):
    """
    KAMIS 일별 시세 API 프록시 (요즘농가 앱용)

    GET /api/kamis/daily-prices/

    KAMIS API를 직접 호출하면 CORS 에러가 발생하므로
    서버에서 프록시 역할을 수행합니다.

    Response:
        KAMIS API 응답 그대로 전달
        {
            "condition": [["20251203"]],
            "error_code": "000",
            "price": [
                {
                    "product_cls_code": "01",
                    "category_code": "100",
                    "category_name": "식량작물",
                    "item_name": "쌀/20kg",
                    "dpr1": "62,451",
                    ...
                },
                ...
            ]
        }
    """
    # 캐시 확인
    cache_key = 'kamis_daily_prices'
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)

    try:
        url = 'https://www.kamis.or.kr/service/price/xml.do'
        params = {
            'action': 'dailySalesList',
            'p_cert_key': KAMIS_API_KEY,
            'p_cert_id': KAMIS_API_ID,
            'p_returntype': 'json',
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # 캐시 저장 (10분)
        cache.set(cache_key, data, KAMIS_CACHE_TIMEOUT)

        return Response(data)

    except requests.exceptions.Timeout:
        return Response(
            {'error': 'KAMIS API 요청 시간 초과'},
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )
    except requests.exceptions.RequestException as e:
        return Response(
            {'error': f'KAMIS API 요청 실패: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except ValueError as e:
        return Response(
            {'error': f'KAMIS API 응답 파싱 실패: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )


# ============================================
# 네이버 데이터랩 API 프록시 (트렌드 모아용)
# ============================================

def _get_naver_headers():
    """네이버 API 공통 헤더"""
    return {
        'X-Naver-Client-Id': NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': NAVER_CLIENT_SECRET,
        'Content-Type': 'application/json',
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def naver_category_trend(request):
    """
    네이버 쇼핑 카테고리 트렌드 API 프록시 (트렌드 모아 앱용)

    POST /api/naver/category-trend/

    Request:
        {
            "categories": [
                { "name": "패션", "code": "50000000" },
                { "name": "가전", "code": "50000003" }
            ],
            "startDate": "2024-06-01",
            "endDate": "2024-12-03",
            "timeUnit": "month",
            "ages": [],
            "gender": ""
        }

    Response:
        {
            "results": [
                {
                    "title": "패션",
                    "category": ["50000000"],
                    "data": [
                        { "period": "2024-06-01", "ratio": 85.5 }
                    ]
                }
            ]
        }
    """
    try:
        categories = request.data.get('categories', [])
        start_date = request.data.get('start_date', request.data.get('startDate'))
        end_date = request.data.get('end_date', request.data.get('endDate'))
        time_unit = request.data.get('time_unit', request.data.get('timeUnit', 'month'))
        ages = request.data.get('ages', [])
        gender = request.data.get('gender', '')

        if not categories or not start_date or not end_date:
            return Response(
                {'error': 'categories, startDate, endDate are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 캐시 키 생성
        cache_key = f"naver_category_trend_{hash(str(categories))}_{start_date}_{end_date}_{time_unit}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        # 네이버 API 요청 포맷
        naver_request = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "category": [
                {"name": cat['name'], "param": [cat['code']]}
                for cat in categories
            ],
        }

        # 선택적 파라미터
        if ages:
            naver_request["ages"] = ages
        if gender:
            naver_request["gender"] = gender

        url = 'https://openapi.naver.com/v1/datalab/shopping/categories'
        response = requests.post(url, headers=_get_naver_headers(), json=naver_request, timeout=30)
        response.raise_for_status()

        data = response.json()

        # 응답 포맷 변환
        result = {"results": []}
        for item in data.get('results', []):
            result["results"].append({
                "title": item.get('title'),
                "category": item.get('category'),
                "data": item.get('data', [])
            })

        # 캐시 저장
        cache.set(cache_key, result, NAVER_DATALAB_CACHE_TIMEOUT)

        return Response(result)

    except requests.exceptions.Timeout:
        return Response(
            {'error': '네이버 API 요청 시간 초과'},
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )
    except requests.exceptions.RequestException as e:
        return Response(
            {'error': f'네이버 API 요청 실패: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"Error in naver_category_trend: {e}")
        return Response(
            {'error': f'Internal server error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def naver_keyword_trend(request):
    """
    네이버 쇼핑 카테고리별 키워드 트렌드 API 프록시 (트렌드 모아 앱용)

    POST /api/naver/keyword-trend/

    Request:
        {
            "categoryCode": "50000000",
            "keywords": [
                { "name": "패딩", "param": ["패딩"] },
                { "name": "코트", "param": ["코트"] }
            ],
            "startDate": "2024-06-01",
            "endDate": "2024-12-03",
            "timeUnit": "month",
            "ages": [],
            "gender": ""
        }

    Response:
        {
            "results": [
                {
                    "title": "패딩",
                    "keyword": ["패딩"],
                    "data": [
                        { "period": "2024-06-01", "ratio": 45.2 }
                    ]
                }
            ]
        }
    """
    try:
        category_code = request.data.get('category_code', request.data.get('categoryCode'))
        keywords = request.data.get('keywords', [])
        start_date = request.data.get('start_date', request.data.get('startDate'))
        end_date = request.data.get('end_date', request.data.get('endDate'))
        time_unit = request.data.get('time_unit', request.data.get('timeUnit', 'month'))
        ages = request.data.get('ages', [])
        gender = request.data.get('gender', '')

        if not category_code or not keywords or not start_date or not end_date:
            return Response(
                {'error': 'categoryCode, keywords, startDate, endDate are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 캐시 키 생성
        cache_key = f"naver_keyword_trend_{category_code}_{hash(str(keywords))}_{start_date}_{end_date}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        # 네이버 API 요청 포맷
        naver_request = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "category": category_code,
            "keyword": keywords,
        }

        # 선택적 파라미터
        if ages:
            naver_request["ages"] = ages
        if gender:
            naver_request["gender"] = gender

        url = 'https://openapi.naver.com/v1/datalab/shopping/category/keywords'
        response = requests.post(url, headers=_get_naver_headers(), json=naver_request, timeout=30)
        response.raise_for_status()

        data = response.json()

        # 응답 포맷 변환
        result = {"results": []}
        for item in data.get('results', []):
            result["results"].append({
                "title": item.get('title'),
                "keyword": item.get('keyword'),
                "data": item.get('data', [])
            })

        # 캐시 저장
        cache.set(cache_key, result, NAVER_DATALAB_CACHE_TIMEOUT)

        return Response(result)

    except requests.exceptions.Timeout:
        return Response(
            {'error': '네이버 API 요청 시간 초과'},
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )
    except requests.exceptions.RequestException as e:
        return Response(
            {'error': f'네이버 API 요청 실패: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"Error in naver_keyword_trend: {e}")
        return Response(
            {'error': f'Internal server error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def naver_search_trend(request):
    """
    네이버 검색어 트렌드 API 프록시 (트렌드 모아 앱 - 선물추천용)

    POST /api/naver/search-trend/

    Request:
        {
            "keywordGroups": [
                { "groupName": "에어팟", "keywords": ["에어팟"] },
                { "groupName": "향수", "keywords": ["향수"] }
            ],
            "startDate": "2024-06-01",
            "endDate": "2024-12-03",
            "timeUnit": "month"
        }

    Response:
        {
            "results": [
                {
                    "title": "에어팟",
                    "keywords": ["에어팟"],
                    "data": [
                        { "period": "2024-06-01", "ratio": 100 }
                    ]
                }
            ]
        }
    """
    try:
        keyword_groups = request.data.get('keyword_groups', request.data.get('keywordGroups', []))
        start_date = request.data.get('start_date', request.data.get('startDate'))
        end_date = request.data.get('end_date', request.data.get('endDate'))
        time_unit = request.data.get('time_unit', request.data.get('timeUnit', 'month'))

        if not keyword_groups or not start_date or not end_date:
            return Response(
                {'error': 'keywordGroups, startDate, endDate are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 캐시 키 생성
        cache_key = f"naver_search_trend_{hash(str(keyword_groups))}_{start_date}_{end_date}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        # 네이버 API 요청 포맷
        naver_request = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "keywordGroups": [
                {"groupName": kg.get('groupName', kg.get('group_name')), "keywords": kg.get('keywords')}
                for kg in keyword_groups
            ],
        }

        url = 'https://openapi.naver.com/v1/datalab/search'
        response = requests.post(url, headers=_get_naver_headers(), json=naver_request, timeout=30)
        response.raise_for_status()

        data = response.json()

        # 응답 포맷 변환
        result = {"results": []}
        for item in data.get('results', []):
            result["results"].append({
                "title": item.get('title'),
                "keywords": item.get('keywords'),
                "data": item.get('data', [])
            })

        # 캐시 저장
        cache.set(cache_key, result, NAVER_DATALAB_CACHE_TIMEOUT)

        return Response(result)

    except requests.exceptions.Timeout:
        return Response(
            {'error': '네이버 API 요청 시간 초과'},
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )
    except requests.exceptions.RequestException as e:
        return Response(
            {'error': f'네이버 API 요청 실패: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"Error in naver_search_trend: {e}")
        return Response(
            {'error': f'Internal server error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# OpenAI 레시피 API (냉장고요리사용)
# ============================================

# mode별 프롬프트 (v3)
RECOMMEND_PROMPTS = {
    'strict': """당신은 한국 요리 전문가입니다.
사용자가 제공한 재료만 사용해서 만들 수 있는 요리를 5~7개 추천해주세요.

[재료]
{ingredients}

[조건]
- 반드시 제공된 재료만 사용 (추가 재료 없이)
- 기본 조미료(소금, 설탕, 간장, 식용유 등)는 있다고 가정
- 한국 가정에서 쉽게 만들 수 있는 요리 위주
- 난이도는 "쉬움", "보통", "어려움" 중 하나
- 시간은 분 단위 숫자만
- usedIngredients: 실제 사용되는 재료 목록
- additionalIngredients: 빈 배열 (strict 모드이므로)

[응답 형식 - 반드시 JSON만 출력]
{{
  "recipes": [
    {{
      "name": "요리명",
      "description": "한 줄 설명 (15자 이내)",
      "difficulty": "쉬움",
      "time": 15,
      "usedIngredients": ["계란", "파"],
      "additionalIngredients": []
    }}
  ]
}}
""",
    'flexible': """당신은 한국 요리 전문가입니다.
사용자가 제공한 재료를 기반으로, 1~2개 정도 간단한 재료만 추가하면 만들 수 있는 요리를 5~7개 추천해주세요.

[재료]
{ingredients}

[조건]
- 제공된 재료를 주로 사용하되, 간단한 재료 1~2개 추가 가능
- 추가 재료는 흔히 구할 수 있는 것으로 (예: 부침가루, 밀가루, 계란 등)
- 기본 조미료(소금, 설탕, 간장, 식용유 등)는 있다고 가정
- 한국 가정에서 쉽게 만들 수 있는 요리 위주
- 난이도는 "쉬움", "보통", "어려움" 중 하나
- 시간은 분 단위 숫자만
- usedIngredients: 제공된 재료 중 실제 사용되는 것
- additionalIngredients: 추가로 필요한 재료 (1~2개)

[응답 형식 - 반드시 JSON만 출력]
{{
  "recipes": [
    {{
      "name": "요리명",
      "description": "한 줄 설명 (15자 이내)",
      "difficulty": "쉬움",
      "time": 15,
      "usedIngredients": ["계란", "파"],
      "additionalIngredients": ["부침가루"]
    }}
  ]
}}
""",
    'open': """당신은 한국 요리 전문가입니다.
사용자가 제공한 재료를 활용하여, 더 맛있게 만들 수 있는 요리를 5~7개 추천해주세요.
재료 추가에 제한이 없으므로 다양한 요리를 추천해주세요.

[재료]
{ingredients}

[조건]
- 제공된 재료를 활용하되, 필요한 재료는 자유롭게 추가
- 기본 조미료(소금, 설탕, 간장, 식용유 등)는 있다고 가정
- 한국 가정에서 쉽게 만들 수 있는 요리 위주
- 난이도는 "쉬움", "보통", "어려움" 중 하나
- 시간은 분 단위 숫자만
- usedIngredients: 제공된 재료 중 실제 사용되는 것
- additionalIngredients: 추가로 필요한 재료 목록

[응답 형식 - 반드시 JSON만 출력]
{{
  "recipes": [
    {{
      "name": "요리명",
      "description": "한 줄 설명 (15자 이내)",
      "difficulty": "쉬움",
      "time": 15,
      "usedIngredients": ["계란", "파"],
      "additionalIngredients": ["돼지고기", "양배추", "부침가루"]
    }}
  ]
}}
"""
}

# 레거시 호환용 (기본값)
RECOMMEND_PROMPT = RECOMMEND_PROMPTS['flexible']

DETAIL_PROMPT = """당신은 한국 요리 전문가입니다.
아래 요리의 상세 레시피를 알려주세요.

[요리명]
{recipe_name}

[사용 가능한 재료]
{ingredients}

[조건]
- 기본 조미료는 있다고 가정
- 초보자도 따라할 수 있게 단계별로 설명
- 요리 팁 2~3개 포함

[응답 형식 - 반드시 JSON만 출력]
{{
  "name": "요리명",
  "description": "한 줄 설명",
  "difficulty": "쉬움/보통/어려움",
  "time": 15,
  "servings": "1인분",
  "ingredients": [
    {{"name": "재료명", "amount": "분량"}}
  ],
  "steps": [
    {{"step": 1, "description": "조리 과정 설명"}}
  ],
  "tips": ["요리 팁1", "요리 팁2"]
}}
"""


def _call_openai(prompt: str) -> dict:
    """OpenAI API 호출 헬퍼 함수"""
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": "You are a helpful Korean cooking assistant. Always respond in valid JSON format only. Do not use markdown code blocks."},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=2000,  # GPT-5는 max_completion_tokens 사용
        response_format={"type": "json_object"}
        # GPT-5-nano는 temperature 지원 안함 (기본값 1 사용)
    )

    content = response.choices[0].message.content
    print(f"OpenAI raw response: {repr(content)}")  # 디버그 로깅

    # JSON 파싱 시도
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        # 마크다운 코드 블록 제거 후 재시도
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())


@api_view(['POST'])
@permission_classes([AllowAny])
def recipe_recommend(request):
    """
    요리 추천 API (냉장고요리사 앱용)

    POST /api/recipes/recommend/

    Request:
        {
            "ingredients": ["계란", "파", "당근", "두부", "양파"]
        }

    Response:
        {
            "success": true,
            "recipes": [
                {
                    "id": "uuid-1234",
                    "name": "계란찜",
                    "description": "부드럽고 담백한 계란찜",
                    "difficulty": "쉬움",
                    "time": 15
                }
            ]
        }
    """
    try:
        ingredients = request.data.get('ingredients', [])

        if not ingredients or len(ingredients) == 0:
            return Response(
                {'success': False, 'error': '재료를 1개 이상 입력해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not OPENAI_API_KEY:
            return Response(
                {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 프롬프트 생성
        prompt = RECOMMEND_PROMPT.format(ingredients=", ".join(ingredients))

        # OpenAI API 호출
        result = _call_openai(prompt)

        # 각 레시피에 UUID 추가
        recipes = result.get('recipes', [])
        for recipe in recipes:
            recipe['id'] = str(uuid.uuid4())

        return Response({
            'success': True,
            'recipes': recipes
        })

    except json.JSONDecodeError as e:
        print(f"JSON parse error in recipe_recommend: {e}")
        return Response(
            {'success': False, 'error': 'AI 응답 파싱 실패'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except openai.APIError as e:
        print(f"OpenAI API error: {e}")
        return Response(
            {'success': False, 'error': f'OpenAI API 오류: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"Error in recipe_recommend: {e}")
        return Response(
            {'success': False, 'error': f'서버 오류: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def recipe_detail(request):
    """
    레시피 상세 API (냉장고요리사 앱용)

    POST /api/recipes/detail/

    Request:
        {
            "recipe_name": "계란찜",
            "ingredients": ["계란", "파", "당근", "두부", "양파"]
        }

    Response:
        {
            "success": true,
            "recipe": {
                "id": "uuid-1234",
                "name": "계란찜",
                "description": "부드럽고 담백한 계란찜",
                "difficulty": "쉬움",
                "time": 15,
                "servings": "1인분",
                "ingredients": [...],
                "steps": [...],
                "tips": [...]
            }
        }
    """
    try:
        recipe_name = request.data.get('recipe_name', request.data.get('recipeName'))
        ingredients = request.data.get('ingredients', [])

        if not recipe_name:
            return Response(
                {'success': False, 'error': '요리명을 입력해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not ingredients or len(ingredients) == 0:
            return Response(
                {'success': False, 'error': '재료를 1개 이상 입력해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not OPENAI_API_KEY:
            return Response(
                {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 프롬프트 생성
        prompt = DETAIL_PROMPT.format(
            recipe_name=recipe_name,
            ingredients=", ".join(ingredients)
        )

        # OpenAI API 호출
        recipe = _call_openai(prompt)

        # UUID 추가
        recipe['id'] = str(uuid.uuid4())

        return Response({
            'success': True,
            'recipe': recipe
        })

    except json.JSONDecodeError as e:
        print(f"JSON parse error in recipe_detail: {e}")
        return Response(
            {'success': False, 'error': 'AI 응답 파싱 실패'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except openai.APIError as e:
        print(f"OpenAI API error: {e}")
        return Response(
            {'success': False, 'error': f'OpenAI API 오류: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"Error in recipe_detail: {e}")
        return Response(
            {'success': False, 'error': f'서버 오류: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# 당근 API (냉장고요리사용)
# ============================================

# 당근 가격표
CARROT_PRODUCTS = {
    'carrots_100': 100,
    'carrots_1000': 1000,
    'carrots_5000': 5000,
    'carrots_10000': 10000,
}

# 당근 비용
CARROT_COST_RECOMMEND = 10  # 요리 추천
CARROT_COST_ANOTHER = 1     # 다른 요리 추천
CARROT_REWARD_AD = 20       # 광고 보상


def _get_or_create_carrot_balance(user):
    """사용자의 당근 잔액 조회 또는 생성"""
    balance, created = CarrotBalance.objects.get_or_create(user=user)
    return balance


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def carrot_balance(request):
    """
    당근 잔액 조회 API

    GET /api/carrots/balance/

    Response:
        { "balance": 50 }
    """
    balance = _get_or_create_carrot_balance(request.user)
    return Response({'balance': balance.balance})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def carrot_reward(request):
    """
    광고 시청 보상 API

    POST /api/carrots/reward/

    Request:
        { "rewardType": "ad_reward" }

    Response:
        {
            "success": true,
            "carrotsEarned": 20,
            "carrotsTotal": 70
        }
    """
    reward_type = request.data.get('reward_type', request.data.get('rewardType', 'ad_reward'))

    if reward_type != 'ad_reward':
        return Response(
            {'success': False, 'error': 'Invalid reward type'},
            status=status.HTTP_400_BAD_REQUEST
        )

    balance = _get_or_create_carrot_balance(request.user)
    new_balance = balance.add_carrots(CARROT_REWARD_AD, 'ad_reward')

    return Response({
        'success': True,
        'carrotsEarned': CARROT_REWARD_AD,
        'carrotsTotal': new_balance
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def carrot_purchase(request):
    """
    당근 구매 API (인앱결제)

    POST /api/carrots/purchase/

    Request:
        {
            "productId": "carrots_1000",
            "orderId": "toss_order_abc123"
        }

    Response:
        {
            "success": true,
            "carrotsPurchased": 1000,
            "carrotsTotal": 1070
        }
    """
    product_id = request.data.get('product_id', request.data.get('productId'))
    order_id = request.data.get('order_id', request.data.get('orderId'))

    if not product_id:
        return Response(
            {'success': False, 'error': 'product_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if product_id not in CARROT_PRODUCTS:
        return Response(
            {'success': False, 'error': f'Invalid product_id: {product_id}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    carrots_amount = CARROT_PRODUCTS[product_id]
    transaction_type = f'purchase_{carrots_amount}'

    balance = _get_or_create_carrot_balance(request.user)
    new_balance = balance.add_carrots(carrots_amount, transaction_type, order_id)

    return Response({
        'success': True,
        'carrotsPurchased': carrots_amount,
        'carrotsTotal': new_balance
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def carrot_history(request):
    """
    당근 거래 내역 조회 API

    GET /api/carrots/history/

    Response:
        {
            "results": [
                {
                    "id": 1,
                    "transactionType": "ad_reward",
                    "transactionTypeDisplay": "광고 시청 보상",
                    "amount": 20,
                    "balanceAfter": 70,
                    "createdAt": "2024-12-06T18:30:00Z"
                }
            ]
        }
    """
    transactions = CarrotTransaction.objects.filter(user=request.user)[:50]

    results = []
    for tx in transactions:
        results.append({
            'id': tx.id,
            'transactionType': tx.transaction_type,
            'transactionTypeDisplay': tx.get_transaction_type_display(),
            'amount': tx.amount,
            'balanceAfter': tx.balance_after,
            'createdAt': tx.created_at.isoformat()
        })

    return Response({'results': results})


# ============================================
# 레시피 API 수정 (당근 차감 로직 추가)
# ============================================

# mode별 ANOTHER 프롬프트 (v3)
ANOTHER_RECIPE_PROMPTS = {
    'strict': """당신은 한국 요리 전문가입니다.
사용자가 제공한 재료만 사용해서 만들 수 있는 요리를 3~5개 추천해주세요.

[재료]
{ingredients}

[제외할 요리 - 이미 추천한 요리]
{exclude_recipes}

[조건]
- 제외할 요리 목록에 있는 요리는 절대 추천하지 마세요
- 반드시 제공된 재료만 사용 (추가 재료 없이)
- 기본 조미료(소금, 설탕, 간장, 식용유 등)는 있다고 가정
- 한국 가정에서 쉽게 만들 수 있는 요리 위주
- 난이도는 "쉬움", "보통", "어려움" 중 하나
- 시간은 분 단위 숫자만

[응답 형식 - 반드시 JSON만 출력]
{{
  "recipes": [
    {{
      "name": "요리명",
      "description": "한 줄 설명 (15자 이내)",
      "difficulty": "쉬움",
      "time": 15,
      "usedIngredients": ["계란", "파"],
      "additionalIngredients": []
    }}
  ]
}}
""",
    'flexible': """당신은 한국 요리 전문가입니다.
사용자가 제공한 재료를 기반으로, 1~2개 정도 간단한 재료만 추가하면 만들 수 있는 요리를 3~5개 추천해주세요.

[재료]
{ingredients}

[제외할 요리 - 이미 추천한 요리]
{exclude_recipes}

[조건]
- 제외할 요리 목록에 있는 요리는 절대 추천하지 마세요
- 제공된 재료를 주로 사용하되, 간단한 재료 1~2개 추가 가능
- 기본 조미료(소금, 설탕, 간장, 식용유 등)는 있다고 가정
- 한국 가정에서 쉽게 만들 수 있는 요리 위주
- 난이도는 "쉬움", "보통", "어려움" 중 하나
- 시간은 분 단위 숫자만

[응답 형식 - 반드시 JSON만 출력]
{{
  "recipes": [
    {{
      "name": "요리명",
      "description": "한 줄 설명 (15자 이내)",
      "difficulty": "쉬움",
      "time": 15,
      "usedIngredients": ["계란", "파"],
      "additionalIngredients": ["부침가루"]
    }}
  ]
}}
""",
    'open': """당신은 한국 요리 전문가입니다.
사용자가 제공한 재료를 활용하여, 더 맛있게 만들 수 있는 요리를 3~5개 추천해주세요.
재료 추가에 제한이 없으므로 다양한 요리를 추천해주세요.

[재료]
{ingredients}

[제외할 요리 - 이미 추천한 요리]
{exclude_recipes}

[조건]
- 제외할 요리 목록에 있는 요리는 절대 추천하지 마세요
- 제공된 재료를 활용하되, 필요한 재료는 자유롭게 추가
- 기본 조미료(소금, 설탕, 간장, 식용유 등)는 있다고 가정
- 한국 가정에서 쉽게 만들 수 있는 요리 위주
- 난이도는 "쉬움", "보통", "어려움" 중 하나
- 시간은 분 단위 숫자만

[응답 형식 - 반드시 JSON만 출력]
{{
  "recipes": [
    {{
      "name": "요리명",
      "description": "한 줄 설명 (15자 이내)",
      "difficulty": "쉬움",
      "time": 15,
      "usedIngredients": ["계란", "파"],
      "additionalIngredients": ["돼지고기", "양배추"]
    }}
  ]
}}
"""
}

# 레거시 호환용
ANOTHER_RECIPE_PROMPT = ANOTHER_RECIPE_PROMPTS['flexible']


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recipe_recommend_with_carrots(request):
    """
    요리 추천 API (당근 10개 차감) - v3

    POST /api/recipes/recommend/

    Request:
        {
            "ingredients": ["계란", "파", "당근", "두부", "양파"],
            "mode": "strict" | "flexible" | "open"  (기본값: flexible)
        }

    Response:
        {
            "success": true,
            "carrotsUsed": 10,
            "carrotsRemaining": 40,
            "recipes": [
                {
                    "id": "uuid",
                    "name": "계란찜",
                    "description": "부드러운 계란찜",
                    "difficulty": "쉬움",
                    "time": 15,
                    "usedIngredients": ["계란", "파"],
                    "additionalIngredients": ["부침가루"]
                }
            ]
        }
    """
    try:
        ingredients = request.data.get('ingredients', [])
        mode = request.data.get('mode', 'flexible')  # strict, flexible, open

        # mode 유효성 검사
        if mode not in ['strict', 'flexible', 'open']:
            mode = 'flexible'

        if not ingredients or len(ingredients) == 0:
            return Response(
                {'success': False, 'error': '재료를 1개 이상 입력해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not OPENAI_API_KEY:
            return Response(
                {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 당근 잔액 확인 및 차감
        balance = _get_or_create_carrot_balance(request.user)
        if not balance.use_carrots(CARROT_COST_RECOMMEND, 'recipe_recommend'):
            return Response({
                'success': False,
                'error': '당근이 부족합니다',
                'carrotsRequired': CARROT_COST_RECOMMEND,
                'carrotsRemaining': balance.balance
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

        # mode에 따른 프롬프트 선택
        prompt_template = RECOMMEND_PROMPTS.get(mode, RECOMMEND_PROMPTS['flexible'])
        prompt = prompt_template.format(ingredients=", ".join(ingredients))

        # OpenAI API 호출
        result = _call_openai(prompt)

        # 각 레시피에 UUID 추가 및 필드 보장
        recipes = result.get('recipes', [])
        for recipe in recipes:
            recipe['id'] = str(uuid.uuid4())
            # usedIngredients, additionalIngredients 필드 보장
            if 'usedIngredients' not in recipe:
                recipe['usedIngredients'] = []
            if 'additionalIngredients' not in recipe:
                recipe['additionalIngredients'] = []

        return Response({
            'success': True,
            'carrotsUsed': CARROT_COST_RECOMMEND,
            'carrotsRemaining': balance.balance,
            'recipes': recipes
        })

    except json.JSONDecodeError as e:
        print(f"JSON parse error in recipe_recommend_with_carrots: {e}")
        return Response(
            {'success': False, 'error': 'AI 응답 파싱 실패'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except openai.APIError as e:
        print(f"OpenAI API error: {e}")
        return Response(
            {'success': False, 'error': f'OpenAI API 오류: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"Error in recipe_recommend_with_carrots: {e}")
        return Response(
            {'success': False, 'error': f'서버 오류: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recipe_another(request):
    """
    다른 요리 추천 API (당근 1개 차감) - v3

    POST /api/recipes/another/

    Request:
        {
            "ingredients": ["계란", "파", "당근", "두부", "양파"],
            "excludeRecipes": ["계란찜", "계란볶음밥"],
            "mode": "strict" | "flexible" | "open"  (기본값: flexible)
        }

    Response:
        {
            "success": true,
            "carrotsUsed": 1,
            "carrotsRemaining": 39,
            "recipes": [
                {
                    "id": "uuid",
                    "name": "계란말이",
                    "description": "폭신한 계란말이",
                    "difficulty": "쉬움",
                    "time": 10,
                    "usedIngredients": ["계란", "파"],
                    "additionalIngredients": []
                }
            ]
        }
    """
    try:
        ingredients = request.data.get('ingredients', [])
        exclude_recipes = request.data.get('exclude_recipes', request.data.get('excludeRecipes', []))
        mode = request.data.get('mode', 'flexible')  # strict, flexible, open

        # mode 유효성 검사
        if mode not in ['strict', 'flexible', 'open']:
            mode = 'flexible'

        if not ingredients or len(ingredients) == 0:
            return Response(
                {'success': False, 'error': '재료를 1개 이상 입력해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not OPENAI_API_KEY:
            return Response(
                {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 당근 잔액 확인 및 차감
        balance = _get_or_create_carrot_balance(request.user)
        if not balance.use_carrots(CARROT_COST_ANOTHER, 'recipe_another'):
            return Response({
                'success': False,
                'error': '당근이 부족합니다',
                'carrotsRequired': CARROT_COST_ANOTHER,
                'carrotsRemaining': balance.balance
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

        # mode에 따른 프롬프트 선택
        exclude_str = ", ".join(exclude_recipes) if exclude_recipes else "없음"
        prompt_template = ANOTHER_RECIPE_PROMPTS.get(mode, ANOTHER_RECIPE_PROMPTS['flexible'])
        prompt = prompt_template.format(
            ingredients=", ".join(ingredients),
            exclude_recipes=exclude_str
        )

        # OpenAI API 호출
        result = _call_openai(prompt)

        # 각 레시피에 UUID 추가 및 필드 보장
        recipes = result.get('recipes', [])
        for recipe in recipes:
            recipe['id'] = str(uuid.uuid4())
            # usedIngredients, additionalIngredients 필드 보장
            if 'usedIngredients' not in recipe:
                recipe['usedIngredients'] = []
            if 'additionalIngredients' not in recipe:
                recipe['additionalIngredients'] = []

        return Response({
            'success': True,
            'carrotsUsed': CARROT_COST_ANOTHER,
            'carrotsRemaining': balance.balance,
            'recipes': recipes
        })

    except json.JSONDecodeError as e:
        print(f"JSON parse error in recipe_another: {e}")
        return Response(
            {'success': False, 'error': 'AI 응답 파싱 실패'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except openai.APIError as e:
        print(f"OpenAI API error: {e}")
        return Response(
            {'success': False, 'error': f'OpenAI API 오류: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"Error in recipe_another: {e}")
        return Response(
            {'success': False, 'error': f'서버 오류: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recipe_detail_auth(request):
    """
    레시피 상세 API (로그인 필요, 무료)

    POST /api/recipes/detail/

    Request:
        {
            "recipeName": "계란찜",
            "ingredients": ["계란", "파", "당근", "두부", "양파"]
        }

    Response:
        {
            "success": true,
            "recipe": { ... }
        }
    """
    try:
        recipe_name = request.data.get('recipe_name', request.data.get('recipeName'))
        ingredients = request.data.get('ingredients', [])

        if not recipe_name:
            return Response(
                {'success': False, 'error': '요리명을 입력해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not ingredients or len(ingredients) == 0:
            return Response(
                {'success': False, 'error': '재료를 1개 이상 입력해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not OPENAI_API_KEY:
            return Response(
                {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 프롬프트 생성
        prompt = DETAIL_PROMPT.format(
            recipe_name=recipe_name,
            ingredients=", ".join(ingredients)
        )

        # OpenAI API 호출
        recipe = _call_openai(prompt)

        # UUID 추가
        recipe['id'] = str(uuid.uuid4())

        # 현재 당근 잔액도 함께 반환
        balance = _get_or_create_carrot_balance(request.user)

        return Response({
            'success': True,
            'carrotsRemaining': balance.balance,
            'recipe': recipe
        })

    except json.JSONDecodeError as e:
        print(f"JSON parse error in recipe_detail_auth: {e}")
        return Response(
            {'success': False, 'error': 'AI 응답 파싱 실패'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except openai.APIError as e:
        print(f"OpenAI API error: {e}")
        return Response(
            {'success': False, 'error': f'OpenAI API 오류: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"Error in recipe_detail_auth: {e}")
        return Response(
            {'success': False, 'error': f'서버 오류: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# 저장된 레시피 API (냉장고요리사용)
# ============================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def saved_recipes_list(request):
    """
    저장된 레시피 목록 조회

    GET /api/recipes/saved/

    Response:
        {
            "success": true,
            "recipes": [
                {
                    "id": "uuid",
                    "name": "계란찜",
                    "description": "부드러운 계란찜",
                    "difficulty": "쉬움",
                    "time": 15,
                    "servings": "2인분",
                    "ingredients": [...],
                    "steps": [...],
                    "tips": [...],
                    "usedIngredients": [...],
                    "additionalIngredients": [...],
                    "savedAt": "2024-12-07T12:00:00Z"
                }
            ]
        }
    """
    from api.models import SavedRecipe

    recipes = SavedRecipe.objects.filter(user=request.user)
    recipe_list = []
    for r in recipes:
        recipe_list.append({
            'id': r.recipe_id,
            'name': r.name,
            'description': r.description,
            'difficulty': r.difficulty,
            'time': r.time,
            'servings': r.servings,
            'ingredients': r.ingredients,
            'steps': r.steps,
            'tips': r.tips,
            'usedIngredients': r.used_ingredients,
            'additionalIngredients': r.additional_ingredients,
            'savedAt': r.saved_at.isoformat()
        })

    return Response({
        'success': True,
        'recipes': recipe_list
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def saved_recipe_create(request):
    """
    레시피 저장

    POST /api/recipes/saved/

    Request:
        {
            "id": "uuid",
            "name": "계란찜",
            "description": "부드러운 계란찜",
            "difficulty": "쉬움",
            "time": 15,
            "servings": "2인분",
            "ingredients": [{name, amount}, ...],
            "steps": [{step, description}, ...],
            "tips": [...],
            "usedIngredients": [...],
            "additionalIngredients": [...]
        }

    Response:
        {
            "success": true,
            "message": "레시피가 저장되었습니다"
        }
    """
    from api.models import SavedRecipe

    recipe_id = request.data.get('id')
    name = request.data.get('name')

    if not recipe_id or not name:
        return Response(
            {'success': False, 'error': 'id와 name은 필수입니다'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 이미 저장된 레시피인지 확인
    if SavedRecipe.objects.filter(user=request.user, recipe_id=recipe_id).exists():
        return Response(
            {'success': False, 'error': '이미 저장된 레시피입니다'},
            status=status.HTTP_400_BAD_REQUEST
        )

    SavedRecipe.objects.create(
        user=request.user,
        recipe_id=recipe_id,
        name=name,
        description=request.data.get('description', ''),
        difficulty=request.data.get('difficulty', '보통'),
        time=request.data.get('time', 0),
        servings=request.data.get('servings', '1인분'),
        ingredients=request.data.get('ingredients', []),
        steps=request.data.get('steps', []),
        tips=request.data.get('tips', []),
        used_ingredients=request.data.get('usedIngredients', request.data.get('used_ingredients', [])),
        additional_ingredients=request.data.get('additionalIngredients', request.data.get('additional_ingredients', []))
    )

    return Response({
        'success': True,
        'message': '레시피가 저장되었습니다'
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def saved_recipe_delete(request, recipe_id):
    """
    저장된 레시피 삭제

    DELETE /api/recipes/saved/<recipe_id>/

    Response:
        {
            "success": true,
            "message": "레시피가 삭제되었습니다"
        }
    """
    from api.models import SavedRecipe

    try:
        recipe = SavedRecipe.objects.get(user=request.user, recipe_id=recipe_id)
        recipe.delete()
        return Response({
            'success': True,
            'message': '레시피가 삭제되었습니다'
        })
    except SavedRecipe.DoesNotExist:
        return Response(
            {'success': False, 'error': '저장된 레시피를 찾을 수 없습니다'},
            status=status.HTTP_404_NOT_FOUND
        )


# =============================================================================
# 고민하니 (WorryHoney) API
# =============================================================================

WORRYHONEY_SYSTEM_PROMPTS = {
    "power_t": """당신은 T 극강 팩폭러입니다. 감정 빼고 팩트만, 솔루션 중심, 냉정한 분석가.

[응답 스타일]
- 반말 사용
- 감정적 위로 없이 바로 문제 분석
- "잠깐, 정리 좀 하자", "객관적으로 보면" 스타일
- 문제를 명확히 짚어주고 해결책 제시
- 마지막에 "지금 당장 할 수 있는 건 뭐야?" 식으로 행동 유도

[응답 예시]
"잠깐, 정리 좀 하자. 지금 네 상황을 객관적으로 보면 문제는 딱 두 가지야.
첫째, 네가 먼저 연락 안 한 거. 둘째, 상대방 반응을 확인도 안 하고
혼자 결론 내린 거. 감정적으로 힘든 건 알겠는데, 그건 해결책이 아니잖아.
지금 당장 할 수 있는 건 뭐야? 그거부터 말해봐."

[규칙]
- 2~3문단으로 간결하게
- 공감/위로보다 분석과 솔루션 중심""",

    "teacher": """당신은 따뜻한 멘토 선생님입니다. 존댓말, 차분하고 지혜로운, 방향을 제시해주는 인생 선배.

[응답 스타일]
- 존댓말 사용
- "그랬군요", "선생님 생각에는" 스타일
- 상대방 입장도 생각해보게 유도
- 급하게 결정하지 않아도 된다고 안심시킴
- 같이 천천히 생각해보자는 느낌

[응답 예시]
"그랬군요. 그 상황에서 많이 힘들었겠어요.
선생님 생각에는, 지금 가장 중요한 건 상대방의 입장도 한번 생각해보는 거예요.
혹시 상대방은 왜 그렇게 행동했을까요?
같이 천천히 생각해보면 답이 보일 거예요. 급하게 결정하지 않아도 괜찮아요."

[규칙]
- 2~3문단으로 차분하게
- 판단보다 이해와 성찰 유도""",

    "power_f": """당신은 F 극강 공감 폭발러입니다. 감정 이입 200%, 일단 공감부터, 편들어주기.

[응답 스타일]
- 반말 사용, 이모티콘 적극 활용 (ㅠㅠ, 💕 등)
- "헐ㅠㅠㅠㅠ 진짜??", "아 너무 속상하다..." 스타일
- 무조건 상대방 편, "네 잘못 아니야 절대!!"
- 해결책보다 감정적 위로 먼저
- 마지막에 "힘들면 언제든 얘기해" 식으로 마무리

[응답 예시]
"헐ㅠㅠㅠㅠ 진짜?? 아 너무 속상하다... 나까지 마음이 아프네ㅠㅠ
진짜 얼마나 힘들었어... 그 상황에서 그런 말 들으면 누구라도 상처받지ㅠㅠ
네 잘못 아니야 절대!! 일단 오늘은 맛있는 거 먹어. 알겠지?
힘들면 언제든 얘기해 나 여기 있어💕"

[규칙]
- 2~3문단으로 따뜻하게
- 분석/조언보다 공감/위로 중심""",

    "friend": """당신은 편한 동네 친구입니다. 반말, 솔직하지만 다정함, 가끔 장난도, 현실적 조언.

[응답 스타일]
- 반말 사용, "ㅋㅋ", ";;" 등 자연스러운 표현
- "야 뭐야ㅋㅋㅋ", "와 좀 심하긴 하네;;" 스타일
- 공감하면서도 솔직하게 (니도 좀 그랬어)
- 너무 자책하지 말라고 하면서 가벼운 해결책 제시
- "어떻게든 되겠지 뭐ㅋㅋ" 식으로 가볍게 마무리

[응답 예시]
"야 뭐야ㅋㅋㅋ 걔가 진짜 그랬어?? 와 좀 심하긴 하네;;
근데 솔직히 말하면 니도 좀 그랬어. 걔 입장에서 보면 좀 섭섭할 수도?
암튼 너무 자책하지 마~ 다 그런 거야.
일단 며칠 쿨하게 있다가 슬쩍 연락해봐. 어떻게든 되겠지 뭐ㅋㅋ"

[규칙]
- 2~3문단으로 가볍게
- 무겁지 않게, 친구처럼 편하게"""
}

WORRYHONEY_CATEGORY_CONTEXT = {
    "연애": "연애, 짝사랑, 이별, 썸, 데이트 관련 고민",
    "사업": "창업, 사업 운영, 투자, 비즈니스 결정 관련 고민",
    "회사": "직장생활, 상사/동료 관계, 이직, 업무 스트레스 관련 고민",
    "학업": "공부, 시험, 진로, 학교생활 관련 고민"
}


def _call_openai_chat(messages: list, system_prompt: str) -> str:
    """OpenAI API 채팅 호출 (고민하니용)"""
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    # 시스템 메시지 + 대화 히스토리
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=full_messages,
        max_completion_tokens=4096,  # GPT-5는 reasoning tokens도 포함하므로 넉넉히 설정
        reasoning_effort="low",  # 빈 응답 방지 - reasoning 최소화
    )

    content = response.choices[0].message.content
    print(f"[WorryHoney] OpenAI response: {repr(content[:100])}...")
    return content.strip()


@api_view(['POST'])
@permission_classes([AllowAny])
def worryhoney_consult(request):
    """
    고민하니 상담 API

    POST /api/worryhoney/consult/

    Request:
        {
            "category": "연애" | "사업" | "회사" | "학업" | "기타 카테고리",
            "mode": "power_t" | "teacher" | "power_f" | "friend",
            "messages": [
                { "role": "user", "content": "첫 번째 고민 내용" },
                { "role": "assistant", "content": "AI의 첫 번째 응답" },
                { "role": "user", "content": "후속 질문" }
            ]
        }

    Modes:
        - power_t: 팩폭작렬 파워 T (냉철, 논리적, 직설)
        - teacher: 고민상담 선생님 (따뜻, 체계적, 인생선배)
        - power_f: 공감백퍼 파워 F (감정공감, 위로, 리액션)
        - friend: 친한친구와 수다 (반말, 캐주얼, 친구)

    Response:
        {
            "success": true,
            "response": "AI의 상담 응답 텍스트"
        }
    """
    try:
        category = request.data.get('category', '')
        mode = request.data.get('mode', 'power_f')  # 기본값: 공감백퍼 파워 F
        messages = request.data.get('messages', [])

        # 유효성 검사
        if not messages or len(messages) == 0:
            return Response(
                {'success': False, 'error': '메시지가 필요합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_modes = ['power_t', 'teacher', 'power_f', 'friend']
        if mode not in valid_modes:
            return Response(
                {'success': False, 'error': f'mode는 {", ".join(valid_modes)} 중 하나여야 합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not OPENAI_API_KEY:
            return Response(
                {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 시스템 프롬프트 구성
        base_prompt = WORRYHONEY_SYSTEM_PROMPTS[mode]
        category_context = WORRYHONEY_CATEGORY_CONTEXT.get(category, f"'{category}' 관련 고민")
        system_prompt = f"{base_prompt}\n\n[상담 분야]\n{category_context}"

        # OpenAI API 호출
        ai_response = _call_openai_chat(messages, system_prompt)

        return Response({
            'success': True,
            'response': ai_response
        })

    except openai.APIError as e:
        print(f"[WorryHoney] OpenAI API error: {e}")
        return Response(
            {'success': False, 'error': f'AI 서비스 오류: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"[WorryHoney] Error: {e}")
        return Response(
            {'success': False, 'error': f'서버 오류: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
