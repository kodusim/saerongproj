from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    SubCategoryViewSet,
    DataSourceViewSet,
    CollectedDataViewSet,
    CrawlLogViewSet,
    subcategory_data_api,
    GameViewSet,
    SubscriptionViewSet,
    PushTokenViewSet,
    notifications_feed,
    toss_disconnect_callback,
    toss_login,
    refresh_token,
    get_current_user,
    logout,
    premium_status,
    grant_premium,
    cancel_premium,
    test_push_notification,
    api_guide
)

app_name = 'api'

# DRF Router 설정
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'subcategories', SubCategoryViewSet, basename='subcategory')
router.register(r'sources', DataSourceViewSet, basename='datasource')
router.register(r'collected-data', CollectedDataViewSet, basename='collecteddata')
router.register(r'crawl-logs', CrawlLogViewSet, basename='crawllog')

# Game Honey API
router.register(r'games', GameViewSet, basename='game')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'push-tokens', PushTokenViewSet, basename='pushtoken')

urlpatterns = [
    path('', include(router.urls)),
    path('notifications/', notifications_feed, name='notifications'),  # 알림 피드 API

    # Toss Authentication
    path('auth/login', toss_login, name='toss-login'),  # 토스 로그인
    path('auth/refresh', refresh_token, name='refresh-token'),  # 토큰 갱신
    path('auth/me', get_current_user, name='current-user'),  # 현재 사용자 정보
    path('auth/logout', logout, name='logout'),  # 로그아웃
    path('auth/disconnect-callback', toss_disconnect_callback, name='toss-disconnect-callback'),  # 토스 연결 끊기 콜백

    # Premium Subscription
    path('premium/status/', premium_status, name='premium-status'),  # 프리미엄 구독 상태 조회
    path('premium/grant/', grant_premium, name='grant-premium'),  # 프리미엄 구독권 부여
    path('premium/cancel/', cancel_premium, name='cancel-premium'),  # 프리미엄 구독 취소

    # Test APIs (개발/디버깅용)
    path('test/push/', test_push_notification, name='test-push'),  # 푸시 알림 테스트

    # API 가이드 (관리자 전용)
    path('guide/', api_guide, name='api-guide'),  # Game Honey API 가이드

    path('<slug:slug>/', subcategory_data_api, name='subcategory-data'),  # 중분류 데이터 API
]
