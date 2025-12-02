import base64
import json
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
from .models import Game, GameCategory, Subscription, PushToken, UserProfile
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

    # 2. 요청 본문 파싱 (JSON 또는 form-data)
    try:
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            data = json.loads(request.body.decode('utf-8'))
        else:
            # form-urlencoded 또는 기타
            data = dict(request.POST)
            # POST dict는 리스트로 값을 반환하므로 첫 번째 값만 추출
            data = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in data.items()}
    except Exception as e:
        print(f"Failed to parse request body: {e}")
        data = {}

    # userKey 추출 (camelCase와 snake_case 모두 지원)
    user_key = data.get('userKey') or data.get('user_key')
    if not user_key:
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

                # 해당 앱이 game_honey이고 다른 앱 토큰이 없으면 전체 삭제
                remaining_tokens = AppUserToken.objects.filter(user=user).count()
                if app.app_id == 'game_honey' and remaining_tokens == 0:
                    # 게임 하니 전용 데이터 삭제
                    user.game_subscriptions.all().delete()
                    user.push_tokens.all().delete()
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

        # 5. JWT 토큰 발급 (우리 서버용)
        access_token = create_jwt_token(user.id, 'access')
        refresh_token = create_jwt_token(user.id, 'refresh')

        # 6. 응답
        return Response({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'toss_user_key': user_key,
                'name': user.first_name,
                'is_new': created
            }
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
            "refresh_token": "eyJ..."
        }

    Response:
        {
            "access_token": "eyJ...(새로운 토큰)"
        }
    """
    refresh_token = request.data.get('refresh_token')

    if not refresh_token:
        return Response(
            {'error': 'refresh_token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # JWT 토큰에서 사용자 찾기
        user = get_user_from_token(refresh_token)

        if not user:
            return Response(
                {'error': 'Invalid refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 새 AccessToken 발급
        new_access_token = create_jwt_token(user.id, 'access')

        return Response({
            'access_token': new_access_token
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
