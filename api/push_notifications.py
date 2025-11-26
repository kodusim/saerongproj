"""
게임 뉴스 푸시 알림 관련 유틸리티
"""
import requests
from django.conf import settings
from .models import Game, Subscription


def get_game_from_subcategory(subcategory):
    """
    SubCategory에서 Game 객체 추출

    SubCategory.slug를 Game.game_id로 매핑합니다.
    예: SubCategory(slug='maplestory') → Game(game_id='maplestory')

    **자동 매핑 규칙:**
    - 새 게임 추가 시: SubCategory 생성 시 slug를 game_id와 동일하게 설정
    - 하드코딩 불필요, DB에 추가만 하면 자동으로 연동됨

    Args:
        subcategory: SubCategory 객체

    Returns:
        Game 객체 또는 None
    """
    # SubCategory.slug를 game_id로 사용 (자동 매핑)
    game_id = subcategory.slug

    try:
        return Game.objects.get(game_id=game_id, is_active=True)
    except Game.DoesNotExist:
        # 매칭되는 Game이 없으면 None 반환 (푸시 알림 스킵)
        return None


def get_subscribers_for_news(game, category):
    """
    특정 게임/카테고리를 구독한 사용자 목록 조회

    Args:
        game: Game 객체
        category: 카테고리 문자열 (예: "공지사항", "이벤트", "업데이트")

    Returns:
        User 객체 리스트
    """
    subscriptions = Subscription.objects.filter(
        game=game,
        category=category
    ).select_related('user')

    return [sub.user for sub in subscriptions]


def send_toss_push_notification(user_keys, title, body, data=None):
    """
    토스 메신저 API를 통해 푸시 알림 발송 (템플릿 기반)

    Args:
        user_keys: 토스 사용자 키 리스트 (BigInteger)
        title: 알림 제목 (템플릿에서는 사용 안 함)
        body: 알림 본문 (템플릿에서는 사용 안 함)
        data: 추가 데이터 (game_id, category 등)

    Returns:
        성공 여부 (boolean)
    """
    if not user_keys:
        return True

    # 토스 메신저 API 엔드포인트 (템플릿 기반)
    base_url = "https://apps-in-toss-api.toss.im"

    # mTLS 인증서 경로
    cert_path = getattr(settings, 'TOSS_CERT_PATH', None)
    key_path = getattr(settings, 'TOSS_KEY_PATH', None)

    if not cert_path or not key_path:
        print("Warning: Toss mTLS certificates not configured. Skipping push notification.")
        return False

    success_count = 0

    # 각 사용자에게 개별 발송
    for user_key in user_keys:
        # 템플릿 코드: gamehoney-news
        template_code = "gamehoney-news"

        # 템플릿 변수
        context = {}
        if data:
            context["game_id"] = data.get("game_id", "게임")
            context["category"] = data.get("category", "소식")

        # 요청 페이로드
        payload = {
            "templateSetCode": template_code,
            "context": context
        }

        # 헤더에 user_key 추가
        headers = {
            "Content-Type": "application/json",
            "x-toss-user-key": str(user_key)
        }

        try:
            response = requests.post(
                f"{base_url}/api-partner/v1/apps-in-toss/messenger/send-message",
                json=payload,
                headers=headers,
                cert=(cert_path, key_path),
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("resultType") == "SUCCESS":
                    print(f"Push notification sent to user {user_key}")
                    success_count += 1
                else:
                    print(f"Failed to send to user {user_key}: {result}")
            else:
                print(f"Failed to send push to user {user_key}: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Error sending push to user {user_key}: {e}")

    return success_count > 0


def notify_subscribers(collected_data):
    """
    새로운 게임 뉴스에 대해 구독자들에게 푸시 알림 발송

    Args:
        collected_data: CollectedData 객체

    Returns:
        발송 성공 여부 (boolean)
    """
    # 1. SubCategory에서 Game 정보 추출
    subcategory = collected_data.source.subcategory
    game = get_game_from_subcategory(subcategory)

    if not game:
        # 매핑되지 않은 SubCategory는 푸시 알림 발송 안 함
        return False

    # 2. DataSource.name을 카테고리로 사용
    category = collected_data.source.name

    # 3. 해당 게임/카테고리를 구독한 사용자 찾기
    subscribers = get_subscribers_for_news(game, category)

    if not subscribers:
        # 구독자가 없으면 알림 발송 안 함
        return False

    # 4. 토스 user_key 추출 (UserProfile에서) + 프리미엄 사용자만 필터링
    from api.models import PremiumSubscription

    user_keys = []
    for user in subscribers:
        try:
            # 4-1. 프리미엄 구독 확인
            if not hasattr(user, 'premium_subscription'):
                continue  # 프리미엄 구독 없음

            premium = user.premium_subscription
            if not premium.is_active:
                continue  # 만료된 프리미엄

            # 4-2. 토스 user_key 확인
            if hasattr(user, 'profile') and user.profile.toss_user_key:
                user_keys.append(user.profile.toss_user_key)
        except Exception:
            pass

    if not user_keys:
        # 토스 연동된 사용자가 없으면 알림 발송 안 함
        return False

    # 5. 알림 제목/본문 생성
    title = f"{game.display_name} {category}"
    body = collected_data.data.get('title', '새로운 소식이 있습니다')

    # 6. 추가 데이터 (클릭 시 이동할 URL 등)
    data = {
        "url": collected_data.data.get('url', ''),
        "game_id": game.display_name,  # 게임 이름 (예: "메이플스토리")
        "category": category,           # 카테고리 이름 (예: "공지사항")
    }

    # 7. 푸시 알림 발송
    return send_toss_push_notification(user_keys, title, body, data)
