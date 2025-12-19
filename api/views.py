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

    print(f"[Recipe] Calling OpenAI with prompt length: {len(prompt)}")

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": "You are a helpful Korean cooking assistant. Always respond in valid JSON format only. Do not use markdown code blocks."},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=5000,  # GPT-5 reasoning 모델: reasoning + output 토큰 합계 (2000은 부족함)
        reasoning_effort="low",  # GPT-5 reasoning 모델 필수 파라미터
        response_format={"type": "json_object"}
        # GPT-5-nano는 temperature 지원 안함 (기본값 1 사용)
    )

    # 전체 응답 디버깅
    print(f"[Recipe] OpenAI response model: {response.model}")
    print(f"[Recipe] OpenAI finish_reason: {response.choices[0].finish_reason}")
    print(f"[Recipe] OpenAI usage: {response.usage}")

    content = response.choices[0].message.content
    print(f"[Recipe] OpenAI raw content: {repr(content)}")  # 디버그 로깅

    # content가 None이거나 빈 경우 처리
    if not content:
        print(f"[Recipe] WARNING: Empty content received! Full response: {response}")
        raise ValueError("OpenAI returned empty response")

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


# =============================================================================
# 드림모아 (DreamMoa) API - 꿈 해몽
# =============================================================================

DREAMMOA_SYSTEM_PROMPT = """당신은 동양/서양 꿈 해몽 전문가입니다.
사용자가 제공한 꿈 정보를 바탕으로 해몽을 제공합니다.

[응답 규칙]
- 꿈의 요소들을 종합하여 의미있는 해석 제공
- 긍정적이고 희망적인 메시지 중심
- type은 "길몽", "평몽", "흉몽" 중 하나
- emoji는 type에 맞게 선택 (길몽: 🌟/🍀/✨, 평몽: 🌙/💭/🔮, 흉몽: ⚠️/🌑/💫)
- summary는 한줄 요약 (20자 내외)
- interpretation은 상세 해몽 (3~4문장)
- advice는 오늘의 조언 (2~3문장)
- 한국어로 응답

[응답 형식 - 반드시 JSON만 출력]
{
  "type": "길몽",
  "emoji": "🌟",
  "summary": "좋은 일이 생길 징조입니다!",
  "interpretation": "이 꿈은 긍정적인 변화와 새로운 시작을 의미합니다...",
  "advice": "오늘 하루 긍정적인 마음으로 보내시면 좋겠습니다..."
}"""


def _call_openai_dreammoa(prompt: str) -> dict:
    """OpenAI API 호출 (드림모아용 - JSON 응답)"""
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": DREAMMOA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=2000,
        reasoning_effort="low",
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    print(f"[DreamMoa] OpenAI raw response: {repr(content[:200])}...")

    # JSON 파싱
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
def dreammoa_interpret(request):
    """
    드림모아 꿈 해몽 API

    POST /api/dreammoa/interpret/

    Request:
        {
            "dream": {
                "who": "가족",
                "when": "밤",
                "where": "집",
                "what": "물",
                "how": "도망치기",
                "feeling": "무서움"
            }
        }

    Response:
        {
            "success": true,
            "result": {
                "type": "길몽",
                "emoji": "🌟",
                "summary": "좋은 일이 생길 징조입니다!",
                "interpretation": "상세 해몽...",
                "advice": "오늘의 조언..."
            }
        }
    """
    try:
        dream = request.data.get('dream', {})

        # 필수 필드 확인
        required_fields = ['who', 'when', 'where', 'what', 'how', 'feeling']
        missing_fields = [f for f in required_fields if not dream.get(f)]

        if missing_fields:
            return Response(
                {'success': False, 'error': f'필수 필드가 누락되었습니다: {", ".join(missing_fields)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not OPENAI_API_KEY:
            return Response(
                {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 육하원칙을 자연스러운 문장으로 조합
        who = dream.get('who')
        when = dream.get('when')
        where = dream.get('where')
        what = dream.get('what')
        how = dream.get('how')
        feeling = dream.get('feeling')

        # 자연스러운 꿈 설명 문장 생성
        dream_sentence = f"{when}에 {where}에서 "
        if who and who != "기억 안 남":
            dream_sentence += f"{who}와(과) 함께 "
        if what and what != "기억 안 남":
            dream_sentence += f"{what}이(가) 나왔고, "
        if how and how != "기억 안 남":
            dream_sentence += f"{how} 상황이었어요. "
        if feeling and feeling != "기억 안 남":
            dream_sentence += f"그때 느낀 감정은 {feeling}이었어요."

        # 프롬프트 생성
        prompt = f"""다음 꿈 내용을 해몽해주세요:

"{dream_sentence}"

위 꿈 내용을 바탕으로 해몽 결과를 JSON 형식으로 응답해주세요.
interpretation에는 꿈의 요소들을 자연스럽게 엮어서 해석해주세요."""

        print(f"[DreamMoa] Interpreting dream: {dream}")

        # OpenAI API 호출 (JSON 응답)
        result = _call_openai_dreammoa(prompt)
        print(f"[DreamMoa] Result: {result}")

        return Response({
            'success': True,
            'result': result
        })

    except json.JSONDecodeError as e:
        print(f"[DreamMoa] JSON parse error: {e}")
        return Response(
            {'success': False, 'error': 'AI 응답 파싱 실패'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except openai.APIError as e:
        print(f"[DreamMoa] OpenAI API error: {e}")
        return Response(
            {'success': False, 'error': f'AI 서비스 오류: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"[DreamMoa] Error: {e}")
        return Response(
            {'success': False, 'error': f'서버 오류: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== MBTI연구소 API ====================

MBTILAB_SYSTEM_PROMPT = """당신은 MBTI 전문가이자 연애/관계 상담사입니다.
사용자의 MBTI와 상대방의 MBTI, 그리고 둘의 관계 유형을 바탕으로 상대방의 심리를 분석하고 조언을 제공합니다.

[분석 원칙]
1. 상대방 MBTI의 특성을 기반으로 행동/심리를 설명
2. 두 MBTI 간의 상호작용 패턴 고려
3. 관계 유형(썸/연애/친구/직장)에 맞는 맞춤 조언
4. 긍정적이고 건설적인 방향으로 안내
5. 공감하면서도 실질적인 도움이 되는 조언

[응답 형식 - 반드시 JSON만 출력]
{
  "targetAnalysis": "상대방 MBTI 심리 분석 (3-4문장)",
  "advice": "맞춤 조언 (3-4문장)",
  "keyPoints": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
  "compatibility": "두 MBTI의 궁합 한줄평"
}"""


def _call_openai_mbtilab(prompt: str) -> dict:
    """OpenAI API 호출 (MBTI연구소용 - JSON 응답)"""
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": MBTILAB_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=2000,
        reasoning_effort="low",
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    print(f"[MBTILab] OpenAI raw response: {repr(content[:200])}...")

    # JSON 파싱
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
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
def mbtilab_analyze(request):
    """MBTI연구소 분석 API"""
    try:
        print(f"[MBTILab] Request data: {request.data}")
        my_mbti = request.data.get('myMbti') or request.data.get('my_mbti', '')
        target_mbti = request.data.get('targetMbti') or request.data.get('target_mbti', '')
        relation = request.data.get('relation', '')
        relation_name = request.data.get('relationName') or request.data.get('relation_name', '')
        question = request.data.get('question', '')

        if not all([my_mbti, target_mbti, relation_name, question]):
            return Response(
                {'success': False, 'error': '필수 필드가 누락되었습니다'},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_mbtis = [
            'INTJ', 'INTP', 'ENTJ', 'ENTP',
            'INFJ', 'INFP', 'ENFJ', 'ENFP',
            'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ',
            'ISTP', 'ISFP', 'ESTP', 'ESFP'
        ]
        if my_mbti.upper() not in valid_mbtis or target_mbti.upper() not in valid_mbtis:
            return Response(
                {'success': False, 'error': '유효하지 않은 MBTI입니다'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not OPENAI_API_KEY:
            return Response(
                {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        prompt = f"""[상황]
- 내 MBTI: {my_mbti}
- 상대방 MBTI: {target_mbti}
- 관계: {relation_name}
- 질문: {question}

위 상황을 바탕으로 상대방의 심리를 분석하고 조언해주세요."""

        print(f"[MBTILab] Analyzing: {my_mbti} -> {target_mbti} ({relation_name})")

        result = _call_openai_mbtilab(prompt)
        print(f"[MBTILab] Result: {result}")

        return Response({
            'success': True,
            'result': result
        })

    except json.JSONDecodeError as e:
        print(f"[MBTILab] JSON parse error: {e}")
        return Response(
            {'success': False, 'error': 'AI 응답 파싱 실패'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except openai.APIError as e:
        print(f"[MBTILab] OpenAI API error: {e}")
        return Response(
            {'success': False, 'error': f'AI 서비스 오류: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"[MBTILab] Error: {e}")
        return Response(
            {'success': False, 'error': f'서버 오류: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================
# 부업메이트 (HustleMate) API
# ============================================================

HUSTLEMATE_PROMPTS = {
    # 블로그 카테고리
    'blog': {
        'default': """당신은 네이버 블로그 전문 작성자입니다.

작성 규칙:
- 말투: 친근한 ~해요체, 적절한 감탄사 활용
- 분량: 800자 이내
- SEO 최적화된 자연스러운 글

입력 정보:
{inputs_text}

위 정보로 블로그 포스팅을 작성해주세요. 반드시 800자 이내로 작성하세요.""",

        '맛집': """당신은 네이버 블로그 맛집 리뷰 전문 작성자입니다.

작성 규칙:
- 말투: 친근한 ~해요체, 감탄사 활용 (와~ 진짜 맛있었어요!)
- 구조: 인트로→가게정보→메뉴소개→맛평가→분위기→총평
- 분량: 800자 이내
- 특징: 생생한 경험담, 솔직한 리뷰

입력 정보:
{inputs_text}

위 정보로 맛집 블로그 포스팅을 작성해주세요.""",

        '제품': """당신은 네이버 블로그 제품 리뷰 전문 작성자입니다.

작성 규칙:
- 말투: 친근하면서 신뢰감 있는 ~해요체
- 구조: 구매계기→개봉기→사용후기→장단점→추천대상
- 분량: 800자 이내
- 특징: 실사용 경험, 객관적 평가

입력 정보:
{inputs_text}

위 정보로 제품 리뷰 블로그 포스팅을 작성해주세요.""",

        '여행': """당신은 네이버 블로그 여행 리뷰 전문 작성자입니다.

작성 규칙:
- 말투: 설렘 가득한 ~해요체
- 구조: 여행개요→일정→명소소개→맛집/숙소→꿀팁→총평
- 분량: 800자 이내
- 특징: 생생한 여행기, 실용적 정보

입력 정보:
{inputs_text}

위 정보로 여행 블로그 포스팅을 작성해주세요.""",

        '일상': """당신은 네이버 블로그 일상 포스팅 전문 작성자입니다.

작성 규칙:
- 말투: 편안하고 친근한 ~해요체
- 구조: 자연스러운 일기체
- 분량: 800자 이내
- 특징: 공감되는 일상, 따뜻한 감성

입력 정보:
{inputs_text}

위 정보로 일상 블로그 포스팅을 작성해주세요.""",

        '정보': """당신은 네이버 블로그 정보성 콘텐츠 전문 작성자입니다.

작성 규칙:
- 말투: 전문적이면서 친근한 ~해요체
- 구조: 서론→본론(핵심정보)→결론(요약)
- 분량: 800자 이내
- 특징: 정확한 정보, 이해하기 쉬운 설명

입력 정보:
{inputs_text}

위 정보로 정보성 블로그 포스팅을 작성해주세요.""",
    },

    # 유튜브 카테고리
    'youtube': {
        'default': """당신은 유튜브 영상 대본 전문 작성자입니다.

작성 규칙:
- 구조: 훅(관심끌기)→인트로→본론→아웃트로(구독유도)
- 분량: 800자 이내
- 특징: 시청자 참여 유도, 자연스러운 말투

입력 정보:
{inputs_text}

위 정보로 유튜브 영상 대본을 작성해주세요.""",

        '정보튜토리얼': """당신은 유튜브 정보/튜토리얼 영상 대본 전문 작성자입니다.

작성 규칙:
- 구조: 훅→문제제시→해결방법→단계별설명→마무리
- 분량: 800자 이내
- 특징: 명확한 설명, 실용적 정보

입력 정보:
{inputs_text}

위 정보로 튜토리얼 영상 대본을 작성해주세요.""",

        '리뷰언박싱': """당신은 유튜브 리뷰/언박싱 영상 대본 전문 작성자입니다.

작성 규칙:
- 구조: 티저→언박싱→첫인상→상세리뷰→총평
- 분량: 800자 이내
- 특징: 솔직한 평가, 구매 결정에 도움

입력 정보:
{inputs_text}

위 정보로 리뷰 영상 대본을 작성해주세요.""",

        '브이로그': """당신은 유튜브 브이로그 영상 대본 전문 작성자입니다.

작성 규칙:
- 구조: 인트로→일상장면들→하이라이트→마무리
- 분량: 800자 이내
- 특징: 자연스러운 나레이션, 감성적

입력 정보:
{inputs_text}

위 정보로 브이로그 대본을 작성해주세요.""",

        '먹방': """당신은 유튜브 먹방 영상 대본 전문 작성자입니다.

작성 규칙:
- 구조: 음식소개→먹는장면설명→맛표현→총평
- 분량: 800자 이내
- 특징: 생생한 맛 표현, ASMR 요소

입력 정보:
{inputs_text}

위 정보로 먹방 영상 대본을 작성해주세요.""",

        '숏츠': """당신은 유튜브 쇼츠 영상 대본 전문 작성자입니다.

작성 규칙:
- 구조: 강렬한훅(1초)→핵심내용→CTA
- 분량: 300자 이내 (60초 영상)
- 특징: 임팩트 있는 시작, 빠른 전개

입력 정보:
{inputs_text}

위 정보로 쇼츠 영상 대본을 작성해주세요. 반드시 300자 이내로!""",
    },

    # 쿠팡파트너스 카테고리
    'coupang': {
        'default': """당신은 쿠팡파트너스 마케팅 콘텐츠 전문 작성자입니다.

작성 규칙:
- 구조: 관심끌기→상품소개→혜택강조→구매유도
- 분량: 500자 이내
- 특징: 구매 욕구 자극, 혜택 강조

입력 정보:
{inputs_text}

위 정보로 쿠팡파트너스 홍보 콘텐츠를 작성해주세요.""",

        '고가전자제품': """당신은 고가 전자제품 쿠팡파트너스 전문 작성자입니다.

작성 규칙:
- 구조: 필요성→스펙비교→가성비분석→구매링크유도
- 분량: 500자 이내
- 특징: 신뢰성, 전문적 분석

입력 정보:
{inputs_text}

위 정보로 고가 전자제품 홍보 콘텐츠를 작성해주세요.""",

        '가성비템': """당신은 가성비 상품 쿠팡파트너스 전문 작성자입니다.

작성 규칙:
- 구조: 발견계기→가격비교→실사용후기→강력추천
- 분량: 500자 이내
- 특징: 가격 메리트 강조

입력 정보:
{inputs_text}

위 정보로 가성비 상품 홍보 콘텐츠를 작성해주세요.""",

        '시즌아이템': """당신은 시즌 아이템 쿠팡파트너스 전문 작성자입니다.

작성 규칙:
- 구조: 시즌필수템→지금사야하는이유→품절주의→구매유도
- 분량: 500자 이내
- 특징: 긴급성, 시즌 강조

입력 정보:
{inputs_text}

위 정보로 시즌 아이템 홍보 콘텐츠를 작성해주세요.""",

        '반복구매': """당신은 반복구매 상품 쿠팡파트너스 전문 작성자입니다.

작성 규칙:
- 구조: 생활필수품→정기배송혜택→가격비교→로켓배송강조
- 분량: 500자 이내
- 특징: 편리함, 경제성

입력 정보:
{inputs_text}

위 정보로 반복구매 상품 홍보 콘텐츠를 작성해주세요.""",

        '틈새상품': """당신은 틈새 상품 쿠팡파트너스 전문 작성자입니다.

작성 규칙:
- 구조: 이런게있었어?→숨은보석발견→사용후기→공유
- 분량: 500자 이내
- 특징: 신기함, 발견의 즐거움

입력 정보:
{inputs_text}

위 정보로 틈새 상품 홍보 콘텐츠를 작성해주세요.""",
    },

    # 스마트스토어 카테고리
    'smartstore': {
        'default': """당신은 네이버 스마트스토어 상품 상세페이지 전문 작성자입니다.

작성 규칙:
- 구조: 헤드카피→상품특징→상세설명→구매혜택→후기유도
- 분량: 800자 이내
- 특징: 구매전환 최적화, SEO 키워드 포함
- 추가: 검색용 키워드 5개 제안

입력 정보:
{inputs_text}

위 정보로 스마트스토어 상품 설명을 작성하고, 마지막에 추천 키워드 5개를 제시해주세요.""",

        '패션의류': """당신은 패션/의류 스마트스토어 상세페이지 전문 작성자입니다.

작성 규칙:
- 구조: 스타일포인트→소재/핏→코디제안→사이즈가이드
- 분량: 800자 이내
- 특징: 감성적 표현, 착용감 강조

입력 정보:
{inputs_text}

위 정보로 패션 상품 설명을 작성하고, 마지막에 추천 키워드 5개를 제시해주세요.""",

        '식품건강': """당신은 식품/건강 스마트스토어 상세페이지 전문 작성자입니다.

작성 규칙:
- 구조: 원산지/성분→효능→섭취방법→보관법→인증정보
- 분량: 800자 이내
- 특징: 신뢰성, 안전성 강조

입력 정보:
{inputs_text}

위 정보로 식품 상품 설명을 작성하고, 마지막에 추천 키워드 5개를 제시해주세요.""",

        '뷰티화장품': """당신은 뷰티/화장품 스마트스토어 상세페이지 전문 작성자입니다.

작성 규칙:
- 구조: 피부고민→성분분석→사용법→비포애프터→피부타입
- 분량: 800자 이내
- 특징: 효과 강조, 성분 신뢰

입력 정보:
{inputs_text}

위 정보로 뷰티 상품 설명을 작성하고, 마지막에 추천 키워드 5개를 제시해주세요.""",

        '생활용품': """당신은 생활용품 스마트스토어 상세페이지 전문 작성자입니다.

작성 규칙:
- 구조: 생활불편해결→제품특징→사용장면→규격정보
- 분량: 800자 이내
- 특징: 실용성, 편리함 강조

입력 정보:
{inputs_text}

위 정보로 생활용품 상품 설명을 작성하고, 마지막에 추천 키워드 5개를 제시해주세요.""",

        '디지털가전': """당신은 디지털/가전 스마트스토어 상세페이지 전문 작성자입니다.

작성 규칙:
- 구조: 핵심스펙→차별점→사용시나리오→AS정보
- 분량: 800자 이내
- 특징: 기술력, 신뢰성 강조

입력 정보:
{inputs_text}

위 정보로 디지털 상품 설명을 작성하고, 마지막에 추천 키워드 5개를 제시해주세요.""",
    },

    # 전자책/온라인강의 카테고리
    'ebook': {
        'default': """당신은 전자책/온라인강의 판매 페이지 전문 작성자입니다.

작성 규칙:
- 구조: 타겟고민공감→해결책제시→커리큘럼→강사소개→수강혜택
- 분량: 800자 이내
- 특징: 변화 약속, 신뢰 구축

입력 정보:
{inputs_text}

위 정보로 전자책/강의 소개 페이지를 작성해주세요.""",

        '자기계발': """당신은 자기계발 콘텐츠 판매 페이지 전문 작성자입니다.

작성 규칙:
- 구조: 현재고민→변화가능성→구체적방법→성공사례→시작유도
- 분량: 800자 이내
- 특징: 동기부여, 실행 가능성

입력 정보:
{inputs_text}

위 정보로 자기계발 콘텐츠 소개를 작성해주세요.""",

        '재테크': """당신은 재테크 콘텐츠 판매 페이지 전문 작성자입니다.

작성 규칙:
- 구조: 재정고민→수익가능성→구체적전략→실적증명→시작방법
- 분량: 800자 이내
- 특징: 수익 강조, 신뢰성

입력 정보:
{inputs_text}

위 정보로 재테크 콘텐츠 소개를 작성해주세요.""",

        'IT개발': """당신은 IT/개발 콘텐츠 판매 페이지 전문 작성자입니다.

작성 규칙:
- 구조: 시장수요→스킬습득→커리큘럼→포트폴리오→취업/이직연계
- 분량: 800자 이내
- 특징: 실무 중심, 커리어 연결

입력 정보:
{inputs_text}

위 정보로 IT 강의 소개를 작성해주세요.""",

        '마케팅': """당신은 마케팅 콘텐츠 판매 페이지 전문 작성자입니다.

작성 규칙:
- 구조: 마케팅트렌드→실전노하우→케이스스터디→성과증명
- 분량: 800자 이내
- 특징: 트렌드, 실전 적용

입력 정보:
{inputs_text}

위 정보로 마케팅 강의 소개를 작성해주세요.""",

        '취미': """당신은 취미 콘텐츠 판매 페이지 전문 작성자입니다.

작성 규칙:
- 구조: 취미의즐거움→배움의과정→완성작품→커뮤니티
- 분량: 800자 이내
- 특징: 즐거움, 성취감

입력 정보:
{inputs_text}

위 정보로 취미 강의 소개를 작성해주세요.""",
    },

    # 인스타그램/숏폼 카테고리
    'instagram': {
        'default': """당신은 인스타그램/숏폼 콘텐츠 전문 작성자입니다.

작성 규칙:
- 구조: 훅→핵심메시지→CTA
- 분량: 300자 이내
- 특징: 짧고 임팩트 있게, 해시태그 필수
- 해시태그 10개 포함

입력 정보:
{inputs_text}

위 정보로 인스타그램 포스팅을 작성하고, 마지막에 해시태그 10개를 추가해주세요.""",

        '피드카드뉴스': """당신은 인스타그램 카드뉴스 전문 작성자입니다.

작성 규칙:
- 구조: 제목슬라이드→내용슬라이드(3-5장)→CTA슬라이드
- 분량: 슬라이드당 50자 이내
- 특징: 정보 전달, 저장 유도

입력 정보:
{inputs_text}

위 정보로 카드뉴스 슬라이드별 텍스트를 작성하고, 해시태그 10개를 추가해주세요.""",

        '릴스': """당신은 인스타그램 릴스 대본 전문 작성자입니다.

작성 규칙:
- 구조: 훅(1초)→본론(25초)→CTA(4초)
- 분량: 200자 이내
- 특징: 트렌디, 중독성

입력 정보:
{inputs_text}

위 정보로 릴스 대본을 작성하고, 해시태그 10개를 추가해주세요.""",

        '스토리': """당신은 인스타그램 스토리 전문 작성자입니다.

작성 규칙:
- 구조: 관심끌기→내용→상호작용유도
- 분량: 100자 이내
- 특징: 즉각적, 참여 유도

입력 정보:
{inputs_text}

위 정보로 스토리 텍스트를 작성하고, 해시태그 5개를 추가해주세요.""",

        '협찬광고': """당신은 인스타그램 협찬/광고 콘텐츠 전문 작성자입니다.

작성 규칙:
- 구조: 자연스러운도입→제품경험→솔직후기→추천
- 분량: 300자 이내
- 특징: 자연스러움, 신뢰감 (유료광고 표시 포함)

입력 정보:
{inputs_text}

위 정보로 협찬 포스팅을 작성하고, 해시태그 10개를 추가해주세요. (유료광고 표시 포함)""",

        '일상': """당신은 인스타그램 일상 포스팅 전문 작성자입니다.

작성 규칙:
- 구조: 감성문구→일상이야기→마무리
- 분량: 200자 이내
- 특징: 공감, 감성

입력 정보:
{inputs_text}

위 정보로 일상 포스팅을 작성하고, 해시태그 10개를 추가해주세요.""",
    },
}


def _call_openai_hustlemate(prompt: str, max_tokens: int = 1500) -> dict:
    """부업메이트용 OpenAI API 호출 헬퍼 함수"""
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    system_prompt = """당신은 콘텐츠 마케팅 전문가입니다.
사용자의 요청에 따라 블로그, 유튜브, 쿠팡파트너스, 스마트스토어, 전자책, 인스타그램 등 다양한 플랫폼에 최적화된 콘텐츠를 작성합니다.

응답 형식 (JSON):
{
    "content": "생성된 콘텐츠 본문",
    "hashtags": ["#해시태그1", "#해시태그2", ...],  // 인스타그램인 경우만
    "keywords": ["키워드1", "키워드2", ...]  // 스마트스토어인 경우만
}

중요: 반드시 유효한 JSON 형식으로만 응답하세요. 마크다운 코드블록을 사용하지 마세요."""

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=max_tokens,
        reasoning_effort="low",
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    print(f"[HustleMate] OpenAI raw response: {repr(content[:200])}...")

    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())


def _format_inputs(inputs: dict) -> str:
    """inputs 딕셔너리를 프롬프트용 텍스트로 변환"""
    lines = []
    for key, value in inputs.items():
        if value:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "- 정보 없음"


@api_view(['POST'])
@permission_classes([AllowAny])
def hustlemate_generate(request):
    """
    부업메이트 콘텐츠 생성 API

    POST /api/hustlemate/generate/

    Request:
        {
            "category": "blog" | "youtube" | "coupang" | "smartstore" | "ebook" | "instagram",
            "subCategory": "맛집" | "제품" | ... (카테고리별 상이),
            "inputs": { ... 카테고리별 입력 필드 }
        }

    Response:
        {
            "success": true,
            "result": {
                "content": "생성된 콘텐츠",
                "hashtags": [...],  // 인스타그램만
                "keywords": [...]   // 스마트스토어만
            }
        }
    """
    try:
        category = request.data.get('category', '')
        sub_category = request.data.get('subCategory', 'default')
        inputs = request.data.get('inputs', {})

        print(f"[HustleMate] Request - category: {category}, subCategory: {sub_category}")
        print(f"[HustleMate] Inputs: {inputs}")

        # 필수 필드 검증
        if not category:
            return Response(
                {'success': False, 'error': '카테고리를 선택해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if category not in HUSTLEMATE_PROMPTS:
            return Response(
                {'success': False, 'error': f'지원하지 않는 카테고리입니다: {category}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not inputs:
            return Response(
                {'success': False, 'error': '입력 정보를 제공해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not OPENAI_API_KEY:
            return Response(
                {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 프롬프트 선택 (서브카테고리가 없으면 default 사용)
        category_prompts = HUSTLEMATE_PROMPTS[category]

        # 직접입력인 경우 default 사용
        if sub_category == '직접입력':
            sub_category = 'default'

        prompt_template = category_prompts.get(sub_category, category_prompts.get('default'))

        # inputs를 텍스트로 변환
        inputs_text = _format_inputs(inputs)

        # 프롬프트 생성
        prompt = prompt_template.format(inputs_text=inputs_text)

        # 토큰 설정 (숏폼은 짧게)
        max_tokens = 1000 if category == 'instagram' or sub_category == '숏츠' else 1500

        # OpenAI API 호출
        result = _call_openai_hustlemate(prompt, max_tokens)

        # 응답 구성
        response_data = {
            'success': True,
            'result': {
                'content': result.get('content', '')
            }
        }

        # 인스타그램인 경우 해시태그 추가
        if category == 'instagram':
            response_data['result']['hashtags'] = result.get('hashtags', [])

        # 스마트스토어인 경우 키워드 추가
        if category == 'smartstore':
            response_data['result']['keywords'] = result.get('keywords', [])

        return Response(response_data)

    except json.JSONDecodeError as e:
        print(f"[HustleMate] JSON parse error: {e}")
        return Response(
            {'success': False, 'error': 'AI 응답 파싱 실패'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except openai.APIError as e:
        print(f"[HustleMate] OpenAI API error: {e}")
        return Response(
            {'success': False, 'error': f'AI 서비스 오류: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"[HustleMate] Error: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {'success': False, 'error': f'서버 오류: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================
# 면접모아 (InterviewMoa) API
# ============================================================

COMPANY_TYPE_NAMES = {
    'large': '대기업',
    'mid': '중견기업',
    'small': '중소기업',
    'public': '공공기관',
    'startup': '스타트업',
    'custom': '직접입력',
}

JOB_TYPE_NAMES = {
    'research': '연구',
    'accounting': '회계',
    'management': '경영',
    'design': '디자인',
    'webdev': '웹개발',
    'appdev': '앱개발',
    'office': '사무직',
    'marketing': '마케팅',
    'sales': '영업',
    'custom': '직접입력',
}


def _call_openai_interview(prompt: str, system_prompt: str, max_tokens: int = 3000) -> dict:
    """면접모아용 OpenAI API 호출 헬퍼 함수"""
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    print(f"[InterviewMoa] Calling OpenAI with prompt length: {len(prompt)}")

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=max_tokens,
        reasoning_effort="low",
        response_format={"type": "json_object"}
    )

    print(f"[InterviewMoa] finish_reason: {response.choices[0].finish_reason}")
    print(f"[InterviewMoa] usage: {response.usage}")

    content = response.choices[0].message.content
    print(f"[InterviewMoa] content length: {len(content) if content else 0}")

    if not content:
        raise ValueError("OpenAI returned empty response")

    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
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
def interviewmoa_questions(request):
    """
    면접 질문 생성 API

    POST /api/interviewmoa/questions/

    Request:
        {
            "companyType": "large",
            "companyName": "삼성전자",
            "jobType": "webdev",
            "jobName": "프론트엔드 개발자"
        }

    Response:
        {
            "questions": ["질문1", "질문2", "질문3", "질문4", "질문5"]
        }
    """
    try:
        # DRF가 camelCase를 snake_case로 변환하므로 둘 다 지원
        company_type = request.data.get('companyType') or request.data.get('company_type', '')
        company_name = request.data.get('companyName') or request.data.get('company_name', '')
        job_type = request.data.get('jobType') or request.data.get('job_type', '')
        job_name = request.data.get('jobName') or request.data.get('job_name', '')

        print(f"[InterviewMoa] Questions request - companyType: {company_type}, companyName: {company_name}, jobType: {job_type}, jobName: {job_name}")

        if not company_type or not job_type:
            return Response(
                {'success': False, 'error': '기업 유형과 직무 유형을 선택해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not OPENAI_API_KEY:
            return Response(
                {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 기업명/직무명 결정
        company_display = company_name if company_type == 'custom' and company_name else COMPANY_TYPE_NAMES.get(company_type, company_type)
        job_display = job_name if job_type == 'custom' and job_name else JOB_TYPE_NAMES.get(job_type, job_type)

        system_prompt = """당신은 한국의 채용 면접 전문가입니다.
기업 유형과 직무에 맞는 실제 면접에서 나올 수 있는 심층 질문을 생성합니다.

응답 형식 (JSON):
{
    "questions": ["질문1", "질문2", "질문3", "질문4", "질문5"]
}

중요: 반드시 5개의 질문을 생성하세요. 유효한 JSON 형식으로만 응답하세요."""

        prompt = f"""다음 조건에 맞는 면접 질문 5개를 생성해주세요.

기업 유형: {company_display}
{f'기업명: {company_name}' if company_name else ''}
직무: {job_display}
{f'상세 직무: {job_name}' if job_name and job_type == 'custom' else ''}

요구사항:
1. 해당 기업 유형의 조직 문화와 특성을 반영한 질문
2. 해당 직무에서 요구되는 역량을 평가하는 질문
3. 경험, 역량, 상황대처, 가치관 등 다양한 유형의 질문 포함
4. 구체적이고 답변하기에 적절한 난이도의 질문
5. 실제 면접에서 자주 나오는 형태의 질문"""

        result = _call_openai_interview(prompt, system_prompt, max_tokens=2000)

        questions = result.get('questions', [])

        return Response({
            'questions': questions
        })

    except json.JSONDecodeError as e:
        print(f"[InterviewMoa] JSON parse error: {e}")
        return Response(
            {'success': False, 'error': 'AI 응답 파싱 실패'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except openai.APIError as e:
        print(f"[InterviewMoa] OpenAI API error: {e}")
        return Response(
            {'success': False, 'error': f'AI 서비스 오류: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"[InterviewMoa Questions] Error: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {'success': False, 'error': f'서버 오류: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def interviewmoa_evaluate(request):
    """
    면접 평가 및 피드백 API

    POST /api/interviewmoa/evaluate/

    Request:
        {
            "companyType": "large",
            "companyName": "삼성전자",
            "jobType": "webdev",
            "jobName": "프론트엔드 개발자",
            "answers": [
                {"question": "질문1", "answer": "답변1"},
                ...
            ]
        }

    Response:
        {
            "totalScore": 78,
            "passed": true,
            "feedbacks": [
                {
                    "question": "질문1",
                    "answer": "답변1",
                    "score": 85,
                    "feedback": "피드백 내용"
                },
                ...
            ]
        }
    """
    try:
        # DRF가 camelCase를 snake_case로 변환하므로 둘 다 지원
        company_type = request.data.get('companyType') or request.data.get('company_type', '')
        company_name = request.data.get('companyName') or request.data.get('company_name', '')
        job_type = request.data.get('jobType') or request.data.get('job_type', '')
        job_name = request.data.get('jobName') or request.data.get('job_name', '')
        answers = request.data.get('answers', [])

        print(f"[InterviewMoa] Evaluate request - companyType: {company_type}, jobType: {job_type}, answers count: {len(answers)}")

        if not answers or len(answers) == 0:
            return Response(
                {'success': False, 'error': '답변 내용을 입력해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not OPENAI_API_KEY:
            return Response(
                {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 기업명/직무명 결정
        company_display = company_name if company_type == 'custom' and company_name else COMPANY_TYPE_NAMES.get(company_type, company_type)
        job_display = job_name if job_type == 'custom' and job_name else JOB_TYPE_NAMES.get(job_type, job_type)

        system_prompt = """당신은 한국의 채용 면접 평가 전문가입니다.
면접 답변을 평가하고 구체적인 피드백을 제공합니다.

응답 형식 (JSON):
{
    "feedbacks": [
        {
            "question": "질문 내용",
            "answer": "답변 내용",
            "score": 0-100 사이 점수,
            "feedback": "구체적인 피드백"
        }
    ]
}

평가 기준:
- 답변의 구체성 (경험, 수치, 사례 포함 여부)
- 논리적 구조 (STAR 기법 등)
- 직무 연관성
- 전달력과 설득력

중요: 유효한 JSON 형식으로만 응답하세요."""

        # 답변 목록 포맷팅
        answers_text = ""
        for i, item in enumerate(answers, 1):
            q = item.get('question', '')
            a = item.get('answer', '')
            answers_text += f"\n[질문 {i}]\n{q}\n\n[답변 {i}]\n{a}\n"

        prompt = f"""다음 면접 답변들을 평가해주세요.

기업 유형: {company_display}
{f'기업명: {company_name}' if company_name else ''}
직무: {job_display}

{answers_text}

각 답변에 대해:
1. 0-100점 사이로 점수를 매겨주세요
2. 좋은 점과 개선할 점을 포함한 구체적인 피드백을 작성해주세요
3. 해당 기업 유형과 직무 맥락에서 평가해주세요"""

        result = _call_openai_interview(prompt, system_prompt, max_tokens=5000)

        feedbacks = result.get('feedbacks', [])

        # 총점 계산
        scores = [f.get('score', 0) for f in feedbacks if isinstance(f.get('score'), (int, float))]
        total_score = round(sum(scores) / len(scores)) if scores else 0
        passed = total_score >= 70

        return Response({
            'totalScore': total_score,
            'passed': passed,
            'feedbacks': feedbacks
        })

    except json.JSONDecodeError as e:
        print(f"[InterviewMoa] JSON parse error: {e}")
        return Response(
            {'success': False, 'error': 'AI 응답 파싱 실패'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except openai.APIError as e:
        print(f"[InterviewMoa Evaluate] OpenAI API error: {e}")
        return Response(
            {'success': False, 'error': f'AI 서비스 오류: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"[InterviewMoa Evaluate] Error: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {'success': False, 'error': f'서버 오류: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================
# 말투교정 (AccentReduction) API
# ============================================================

ACCENT_CATEGORY_NAMES = {
    'company': '회사',
    'research': '연구',
    'school': '학교',
    'parttime': '알바',
    'friends': '친구',
    'ceremony': '경조사',
    'custom': '직접입력',
}

ACCENT_SUBCATEGORY_NAMES = {
    # 회사
    'boss': '상사에게',
    'colleague': '동료에게',
    'client': '거래처에',
    'email': '업무이메일',
    # 연구
    'professor': '교수님께',
    'researcher': '연구원에게',
    'academic': '논문/학술',
    # 학교
    'teacher': '선생님께',
    'senior': '선배에게',
    'junior': '후배에게',
    'assignment': '과제',
    # 알바
    'owner': '사장님께',
    'customer': '손님에게',
    'schedule': '스케줄',
    # 친구
    'daily': '일상',
    'apology': '사과',
    'request': '부탁',
    # 경조사
    'wedding': '결혼',
    'birthday': '생일',
    'condolence': '조의',
    'promotion': '승진',
    # 직접입력
    'custom': '직접입력',
}

ACCENT_PROMPTS = {
    'company': {
        'boss': """상사에게 보내는 메시지입니다.
- 존댓말(합쇼체/해요체) 사용
- 격식있고 예의바른 표현
- 업무적이면서도 공손한 어투""",
        'colleague': """동료에게 보내는 메시지입니다.
- 존댓말(해요체) 사용
- 친근하면서도 예의있는 표현
- 협조적인 어투""",
        'client': """거래처/클라이언트에게 보내는 메시지입니다.
- 격식있는 존댓말(합쇼체) 사용
- 비즈니스 매너를 갖춘 표현
- 전문적이고 신뢰감 있는 어투""",
        'email': """업무 이메일입니다.
- 격식있는 문어체 사용
- 명확하고 간결한 표현
- 이메일 형식에 맞는 구조""",
    },
    'research': {
        'professor': """교수님께 보내는 메시지입니다.
- 최고 존칭 사용
- 학문적 예의를 갖춘 표현
- 공손하고 격식있는 어투""",
        'researcher': """연구원/동료 연구자에게 보내는 메시지입니다.
- 존댓말 사용
- 학술적이면서 친근한 표현
- 협력적인 어투""",
        'academic': """논문/학술 문서입니다.
- 학술적 문어체 사용
- 객관적이고 논리적인 표현
- 전문 용어 적절히 사용""",
    },
    'school': {
        'teacher': """선생님께 보내는 메시지입니다.
- 최고 존칭 사용
- 공손하고 예의바른 표현
- 학생으로서 예의를 갖춘 어투""",
        'senior': """선배에게 보내는 메시지입니다.
- 존댓말 사용
- 친근하면서도 예의있는 표현
- 후배로서 예의를 갖춘 어투""",
        'junior': """후배에게 보내는 메시지입니다.
- 해요체 또는 반말 사용 가능
- 친근하고 따뜻한 표현
- 선배로서 배려있는 어투""",
        'assignment': """과제/리포트입니다.
- 학술적 문어체 사용
- 논리적이고 명확한 표현
- 과제 형식에 맞는 구조""",
    },
    'parttime': {
        'owner': """사장님/점장님께 보내는 메시지입니다.
- 존댓말(합쇼체/해요체) 사용
- 공손하고 성실한 표현
- 직원으로서 예의를 갖춘 어투""",
        'customer': """손님에게 하는 말입니다.
- 존댓말 사용
- 친절하고 서비스 마인드 있는 표현
- 고객 응대에 적합한 어투""",
        'schedule': """스케줄/근무 관련 메시지입니다.
- 존댓말 사용
- 명확하고 간결한 표현
- 업무적인 어투""",
    },
    'friends': {
        'daily': """친구에게 보내는 일상 메시지입니다.
- 반말 또는 친근한 해요체
- 편안하고 자연스러운 표현
- 친근한 어투""",
        'apology': """친구에게 사과하는 메시지입니다.
- 진심어린 사과 표현
- 솔직하고 진정성 있는 표현
- 관계 회복을 위한 어투""",
        'request': """친구에게 부탁하는 메시지입니다.
- 친근하면서도 정중한 표현
- 부담주지 않는 표현
- 배려있는 어투""",
    },
    'ceremony': {
        'wedding': """결혼 축하 메시지입니다.
- 격식있는 축하 표현
- 진심어린 축복의 말
- 경사에 어울리는 어투""",
        'birthday': """생일 축하 메시지입니다.
- 따뜻한 축하 표현
- 진심어린 축복의 말
- 상대방과의 관계에 맞는 어투""",
        'condolence': """조의/위로 메시지입니다.
- 격식있는 애도 표현
- 진심어린 위로의 말
- 조심스럽고 예의바른 어투""",
        'promotion': """승진 축하 메시지입니다.
- 격식있는 축하 표현
- 진심어린 축하의 말
- 비즈니스 관계에 맞는 어투""",
    },
}


def _call_openai_accent(message: str, context: str) -> dict:
    """말투교정용 OpenAI API 호출 헬퍼 함수"""
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    system_prompt = """당신은 한국어 말투 교정 전문가입니다.
사용자의 메시지를 상황에 맞는 적절한 말투로 교정해주세요.

응답 형식 (JSON):
{
    "correctedMessage": "교정된 메시지",
    "tips": ["교정 팁1", "교정 팁2", "교정 팁3"]
}

규칙:
1. 원본 메시지의 의미와 내용을 유지하면서 말투만 교정
2. 상황에 맞는 적절한 존칭과 어미 사용
3. 자연스럽고 실제로 사용할 수 있는 표현으로 교정
4. 교정 팁은 2-3개 제공 (왜 이렇게 바꿨는지 설명)

중요: 반드시 유효한 JSON 형식으로만 응답하세요."""

    prompt = f"""{context}

원본 메시지:
"{message}"

위 메시지를 상황에 맞게 교정해주세요."""

    print(f"[AccentReduction] Calling OpenAI with message length: {len(message)}")

    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=2000,
        reasoning_effort="low",
        response_format={"type": "json_object"}
    )

    print(f"[AccentReduction] finish_reason: {response.choices[0].finish_reason}")

    content = response.choices[0].message.content

    if not content:
        raise ValueError("OpenAI returned empty response")

    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
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
def accentreduction_correct(request):
    """
    말투 교정 API

    POST /api/accentreduction/correct/

    Request:
        {
            "category": "company",
            "categoryName": "회사",
            "subCategory": "boss",
            "subCategoryName": "상사에게",
            "situation": "업무 보고",
            "message": "팀장님 그 건 제가 내일까지 해놓을게요"
        }

    Response:
        {
            "correctedMessage": "팀장님, 해당 건은 내일까지 완료하여 보고드리겠습니다.",
            "tips": ["존칭 사용으로 예의를 갖추었습니다", ...]
        }
    """
    try:
        # DRF가 camelCase를 snake_case로 변환하므로 둘 다 지원
        category = request.data.get('category') or request.data.get('category', '')
        category_name = request.data.get('categoryName') or request.data.get('category_name', '')
        sub_category = request.data.get('subCategory') or request.data.get('sub_category', '')
        sub_category_name = request.data.get('subCategoryName') or request.data.get('sub_category_name', '')
        situation = request.data.get('situation', '')
        message = request.data.get('message', '')

        print(f"[AccentReduction] Request - category: {category}, subCategory: {sub_category}, message length: {len(message)}")

        if not message or not message.strip():
            return Response(
                {'success': False, 'error': '교정할 메시지를 입력해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not category:
            return Response(
                {'success': False, 'error': '카테고리를 선택해주세요'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not OPENAI_API_KEY:
            return Response(
                {'success': False, 'error': 'OpenAI API 키가 설정되지 않았습니다'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 컨텍스트 생성
        cat_display = category_name or ACCENT_CATEGORY_NAMES.get(category, category)
        subcat_display = sub_category_name or ACCENT_SUBCATEGORY_NAMES.get(sub_category, sub_category)

        # 프롬프트 컨텍스트 선택
        if category == 'custom':
            context = f"""직접 입력한 상황입니다.
상황 설명: {situation if situation else '일반적인 상황'}
- 상황에 맞는 적절한 말투로 교정해주세요."""
        else:
            category_prompts = ACCENT_PROMPTS.get(category, {})
            base_context = category_prompts.get(sub_category, f"{cat_display}에서 {subcat_display} 메시지입니다.")

            context = base_context
            if situation:
                context += f"\n상황: {situation}"

        # OpenAI API 호출
        result = _call_openai_accent(message, context)

        return Response({
            'correctedMessage': result.get('correctedMessage', ''),
            'tips': result.get('tips', [])
        })

    except json.JSONDecodeError as e:
        print(f"[AccentReduction] JSON parse error: {e}")
        return Response(
            {'success': False, 'error': 'AI 응답 파싱 실패'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except openai.APIError as e:
        print(f"[AccentReduction] OpenAI API error: {e}")
        return Response(
            {'success': False, 'error': f'AI 서비스 오류: {str(e)}'},
            status=status.HTTP_502_BAD_GATEWAY
        )
    except Exception as e:
        print(f"[AccentReduction] Error: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {'success': False, 'error': f'서버 오류: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
