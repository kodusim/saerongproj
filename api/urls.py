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
    notifications_feed
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
    path('<slug:slug>/', subcategory_data_api, name='subcategory-data'),  # 중분류 데이터 API
]
