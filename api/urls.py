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
    api_guide,
    crawler_status,
    kamis_daily_prices,
    # 네이버 데이터랩 API (트렌드 모아용)
    naver_category_trend,
    naver_keyword_trend,
    naver_search_trend,
    # OpenAI 레시피 API (냉장고요리사용) - 레거시 (AllowAny)
    recipe_recommend,
    recipe_detail,
    # 냉장고요리사 API (인증 필요, 당근 시스템)
    carrot_balance,
    carrot_reward,
    carrot_purchase,
    carrot_history,
    recipe_recommend_with_carrots,
    recipe_another,
    recipe_detail_auth,
    saved_recipes_list,
    saved_recipe_create,
    saved_recipe_delete,
    # 고민하니 API
    worryhoney_consult,
    # 드림모아 API
    dreammoa_interpret,
    # MBTI연구소 API
    mbtilab_analyze,
    # 부업메이트 API
    hustlemate_generate,
    # 면접모아 API
    interviewmoa_questions,
    interviewmoa_evaluate,
    # 말투교정 API
    accentreduction_correct,
    # 스트레스코치 API
    stresscoach_analyze,
    # 이슈모아 API
    issuemoa_categories,
    issuemoa_issues,
    issuemoa_issue_detail,
    issuemoa_weekly_summary,
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
    path('auth/disconnect-callback', toss_disconnect_callback, name='toss-disconnect-callback'),  # 토스 연결 끊기 콜백 (기존 - game_honey)
    path('auth/disconnect-callback/<str:app_id>', toss_disconnect_callback, name='toss-disconnect-callback-app'),  # 토스 연결 끊기 콜백 (앱별)

    # Premium Subscription
    path('premium/status/', premium_status, name='premium-status'),  # 프리미엄 구독 상태 조회
    path('premium/grant/', grant_premium, name='grant-premium'),  # 프리미엄 구독권 부여
    path('premium/cancel/', cancel_premium, name='cancel-premium'),  # 프리미엄 구독 취소

    # Test APIs (개발/디버깅용)
    path('test/push/', test_push_notification, name='test-push'),  # 푸시 알림 테스트

    # API 가이드 (관리자 전용)
    path('guide/', api_guide, name='api-guide'),  # Game Honey API 가이드

    # Crawler Status
    path('crawler/status/', crawler_status, name='crawler-status'),  # 크롤러 상태 조회

    # KAMIS API 프록시 (요즘농가용)
    path('kamis/daily-prices/', kamis_daily_prices, name='kamis-daily-prices'),  # KAMIS 일별 시세

    # 네이버 데이터랩 API 프록시 (트렌드 모아용)
    path('naver/category-trend/', naver_category_trend, name='naver-category-trend'),  # 쇼핑 카테고리 트렌드
    path('naver/keyword-trend/', naver_keyword_trend, name='naver-keyword-trend'),  # 쇼핑 키워드 트렌드
    path('naver/search-trend/', naver_search_trend, name='naver-search-trend'),  # 검색어 트렌드

    # OpenAI 레시피 API (냉장고요리사용) - 레거시 (AllowAny, 당근 차감 없음)
    # path('recipes/recommend/', recipe_recommend, name='recipe-recommend'),  # 레거시 - 비활성화
    # path('recipes/detail/', recipe_detail, name='recipe-detail'),  # 레거시 - 비활성화

    # 냉장고요리사 API (인증 필요, 당근 시스템)
    path('carrots/balance/', carrot_balance, name='carrot-balance'),  # 당근 잔액 조회
    path('carrots/reward/', carrot_reward, name='carrot-reward'),  # 광고 보상 (+20)
    path('carrots/purchase/', carrot_purchase, name='carrot-purchase'),  # 당근 구매
    path('carrots/history/', carrot_history, name='carrot-history'),  # 거래 내역

    path('recipes/recommend/', recipe_recommend_with_carrots, name='recipe-recommend'),  # 요리 추천 (당근 -10)
    path('recipes/detail/', recipe_detail_auth, name='recipe-detail'),  # 레시피 상세 (무료)
    path('recipes/another/', recipe_another, name='recipe-another'),  # 다른 요리 추천 (당근 -1)
    path('recipes/saved/', saved_recipes_list, name='saved-recipes-list'),  # 저장된 레시피 목록 (GET)
    path('recipes/saved/create/', saved_recipe_create, name='saved-recipe-create'),  # 레시피 저장 (POST)
    path('recipes/saved/<str:recipe_id>/', saved_recipe_delete, name='saved-recipe-delete'),  # 저장된 레시피 삭제 (DELETE)

    # 고민하니 API (WorryHoney)
    path('worryhoney/consult/', worryhoney_consult, name='worryhoney-consult'),  # AI 상담

    # 드림모아 API (DreamMoa)
    path('dreammoa/interpret/', dreammoa_interpret, name='dreammoa-interpret'),  # 꿈 해몽

    # MBTI연구소 API (MBTILab)
    path('mbtilab/analyze/', mbtilab_analyze, name='mbtilab-analyze'),  # MBTI 분석

    # 부업메이트 API (HustleMate)
    path('hustlemate/generate/', hustlemate_generate, name='hustlemate-generate'),  # 콘텐츠 생성

    # 면접모아 API (InterviewMoa)
    path('interviewmoa/questions/', interviewmoa_questions, name='interviewmoa-questions'),  # 면접 질문 생성
    path('interviewmoa/evaluate/', interviewmoa_evaluate, name='interviewmoa-evaluate'),  # 면접 평가

    # 말투교정 API (AccentReduction)
    path('accentreduction/correct/', accentreduction_correct, name='accentreduction-correct'),  # 말투 교정

    # 스트레스코치 API (StressCoach)
    path('stresscoach/analyze/', stresscoach_analyze, name='stresscoach-analyze'),  # 스트레스 분석

    # 이슈모아 API (IssueMoa)
    path('issuemoa/categories/', issuemoa_categories, name='issuemoa-categories'),  # 카테고리 목록
    path('issuemoa/issues/', issuemoa_issues, name='issuemoa-issues'),  # 이슈 목록
    path('issuemoa/issues/<int:issue_id>/', issuemoa_issue_detail, name='issuemoa-issue-detail'),  # 이슈 상세
    path('issuemoa/weekly-summary/', issuemoa_weekly_summary, name='issuemoa-weekly-summary'),  # 주간 요약

    path('<slug:slug>/', subcategory_data_api, name='subcategory-data'),  # 중분류 데이터 API
]
