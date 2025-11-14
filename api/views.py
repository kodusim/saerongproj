from rest_framework import viewsets, filters, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from core.models import Category, SubCategory
from sources.models import DataSource
from collector.models import CollectedData, CrawlLog
from .models import Game, GameCategory, Subscription, PushToken
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
