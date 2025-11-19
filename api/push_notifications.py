"""
게임 뉴스 푸시 알림 관련 유틸리티
"""
import requests
from django.conf import settings
from .models import Game, Subscription


# SubCategory 이름 → Game game_id 매핑
SUBCATEGORY_TO_GAME_MAPPING = {
    "메이플스토리": "maplestory",
    # 향후 다른 게임 추가 시 여기에 추가
    # "로스트아크": "lostark",
    # "던전앤파이터": "dungeon_and_fighter",
}


def get_game_from_subcategory(subcategory):
    """
    SubCategory에서 Game 객체 추출

    Args:
        subcategory: SubCategory 객체

    Returns:
        Game 객체 또는 None
    """
    game_id = SUBCATEGORY_TO_GAME_MAPPING.get(subcategory.name)
    if not game_id:
        return None

    try:
        return Game.objects.get(game_id=game_id, is_active=True)
    except Game.DoesNotExist:
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
    토스 메신저 API를 통해 푸시 알림 발송

    Args:
        user_keys: 토스 사용자 키 리스트 (BigInteger)
        title: 알림 제목
        body: 알림 본문
        data: 추가 데이터 (딕셔너리, optional)

    Returns:
        성공 여부 (boolean)
    """
    if not user_keys:
        return True

    # 토스 메신저 API 엔드포인트
    # https://toss.im/tossim-console/docs/apps-in-toss/push
    url = "https://toss.im/api/v1/apps-in-toss/push"

    # mTLS 인증서 경로 (settings에서 가져오기)
    cert_path = getattr(settings, 'TOSS_CERT_PATH', None)
    key_path = getattr(settings, 'TOSS_KEY_PATH', None)

    if not cert_path or not key_path:
        print("Warning: Toss mTLS certificates not configured. Skipping push notification.")
        return False

    # 요청 페이로드
    payload = {
        "userKeys": user_keys,  # 토스 사용자 키 리스트
        "notification": {
            "title": title,
            "body": body,
        }
    }

    if data:
        payload["data"] = data

    try:
        response = requests.post(
            url,
            json=payload,
            cert=(cert_path, key_path),  # mTLS 인증서
            timeout=10
        )

        if response.status_code == 200:
            print(f"Push notification sent successfully to {len(user_keys)} users")
            return True
        else:
            print(f"Failed to send push notification: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"Error sending push notification: {e}")
        return False


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

    # 4. 토스 user_key 추출 (UserProfile에서)
    user_keys = []
    for user in subscribers:
        try:
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
        "gameId": game.game_id,
        "category": category,
    }

    # 7. 푸시 알림 발송
    return send_toss_push_notification(user_keys, title, body, data)
