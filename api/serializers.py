from rest_framework import serializers
from django.contrib.auth.models import User
from core.models import Category, SubCategory
from sources.models import DataSource
from collector.models import CollectedData, CrawlLog
from .models import Game, GameCategory, Subscription, PushToken, UserProfile, PremiumSubscription


class CategorySerializer(serializers.ModelSerializer):
    """카테고리 Serializer"""

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'is_active', 'order', 'created_at']


class SubCategorySerializer(serializers.ModelSerializer):
    """서브카테고리 Serializer"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    icon = serializers.SerializerMethodField()

    class Meta:
        model = SubCategory
        fields = ['id', 'category', 'category_name', 'name', 'slug', 'icon', 'is_active', 'created_at']

    def get_icon(self, obj):
        """아이콘 이미지 URL 반환"""
        request = self.context.get('request')
        if obj.icon_image:
            if request:
                return request.build_absolute_uri(obj.icon_image.url)
            return obj.icon_image.url
        return None


class DataSourceSerializer(serializers.ModelSerializer):
    """데이터 소스 Serializer"""
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    category_name = serializers.CharField(source='subcategory.category.name', read_only=True)

    class Meta:
        model = DataSource
        fields = [
            'id', 'subcategory', 'subcategory_name', 'category_name',
            'name', 'url', 'crawler_type', 'crawler_class',
            'crawl_interval', 'is_active', 'last_crawled_at', 'created_at'
        ]


class CollectedDataSerializer(serializers.ModelSerializer):
    """수집된 데이터 Serializer"""
    source_name = serializers.CharField(source='source.name', read_only=True)
    subcategory_name = serializers.CharField(source='source.subcategory.name', read_only=True)
    category_name = serializers.CharField(source='source.subcategory.category.name', read_only=True)

    class Meta:
        model = CollectedData
        fields = [
            'id', 'source', 'source_name', 'subcategory_name', 'category_name',
            'data', 'hash_key', 'collected_at'
        ]


class CollectedDataListSerializer(serializers.ModelSerializer):
    """수집된 데이터 목록용 간소화된 Serializer"""
    source_name = serializers.CharField(source='source.name', read_only=True)
    title = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()

    class Meta:
        model = CollectedData
        fields = ['id', 'source_name', 'title', 'category', 'date', 'collected_at']

    def get_title(self, obj):
        return obj.data.get('title', '')

    def get_category(self, obj):
        return obj.data.get('category', '')

    def get_date(self, obj):
        return obj.data.get('date', '')


class CrawlLogSerializer(serializers.ModelSerializer):
    """크롤링 로그 Serializer"""
    source_name = serializers.CharField(source='source.name', read_only=True)

    class Meta:
        model = CrawlLog
        fields = [
            'id', 'source', 'source_name', 'status', 'items_collected',
            'error_message', 'started_at', 'completed_at', 'duration_seconds'
        ]


# ============================================
# Game Honey API Serializers
# ============================================

class GameCategorySerializer(serializers.ModelSerializer):
    """게임 카테고리 Serializer"""

    class Meta:
        model = GameCategory
        fields = ['id', 'name', 'created_at']


class GameSerializer(serializers.ModelSerializer):
    """게임 Serializer"""
    categories = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = ['id', 'game_id', 'display_name', 'icon_url', 'icon', 'is_active', 'categories', 'created_at']

    def get_categories(self, obj):
        """게임의 카테고리 목록 반환"""
        categories = obj.categories.all()
        return [cat.name for cat in categories]

    def get_icon(self, obj):
        """아이콘 이미지 URL 반환 (업로드된 이미지 우선, 없으면 icon_url)"""
        request = self.context.get('request')
        if obj.icon_image:
            if request:
                return request.build_absolute_uri(obj.icon_image.url)
            return obj.icon_image.url
        return obj.icon_url if obj.icon_url else None


class SubscriptionSerializer(serializers.ModelSerializer):
    """구독 Serializer"""
    game_id = serializers.CharField(source='game.game_id', read_only=True)
    game_name = serializers.CharField(source='game.display_name', read_only=True)

    class Meta:
        model = Subscription
        fields = ['id', 'game', 'game_id', 'game_name', 'category', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        """구독 유효성 검사"""
        user = self.context['request'].user
        game = data.get('game')
        category = data.get('category')

        # 중복 구독 확인
        if Subscription.objects.filter(user=user, game=game, category=category).exists():
            raise serializers.ValidationError("이미 구독 중입니다.")

        return data


class SubscriptionCreateSerializer(serializers.Serializer):
    """구독 생성 Serializer (game_id 문자열로 받기)"""
    game_id = serializers.CharField()
    category = serializers.CharField()

    def validate_game_id(self, value):
        """게임 ID 유효성 검사"""
        try:
            game = Game.objects.get(game_id=value, is_active=True)
        except Game.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 게임입니다.")
        return value

    def create(self, validated_data):
        """구독 생성"""
        user = self.context['request'].user
        game = Game.objects.get(game_id=validated_data['game_id'])
        category = validated_data['category']

        subscription, created = Subscription.objects.get_or_create(
            user=user,
            game=game,
            category=category
        )

        return subscription


class PushTokenSerializer(serializers.ModelSerializer):
    """푸시 토큰 Serializer"""

    class Meta:
        model = PushToken
        fields = ['id', 'token', 'device_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """사용자 Serializer"""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class NotificationSerializer(serializers.Serializer):
    """알림 피드 Serializer (구독한 게임의 최신 소식)"""
    game = serializers.CharField()
    game_id = serializers.CharField()
    category = serializers.CharField()
    title = serializers.CharField()
    url = serializers.URLField()
    date = serializers.CharField()
    collected_at = serializers.DateTimeField()


class PremiumSubscriptionSerializer(serializers.ModelSerializer):
    """프리미엄 구독 Serializer"""
    is_premium = serializers.SerializerMethodField()

    class Meta:
        model = PremiumSubscription
        fields = ['id', 'subscription_type', 'expires_at', 'is_premium', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_is_premium(self, obj):
        """현재 활성화된 구독인지 확인"""
        return obj.is_active


class PremiumGrantSerializer(serializers.Serializer):
    """프리미엄 구독권 부여 Serializer"""
    subscription_type = serializers.ChoiceField(choices=['free_ad', 'premium'])
    order_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    days = serializers.ChoiceField(
        choices=[30, 90, 180, 365],
        required=False,
        help_text="프리미엄 구독 기간 (일). free_ad는 고정 7일, premium은 30/90/180/365일 선택 가능"
    )

    def validate(self, data):
        """premium 타입일 때 days 검증"""
        subscription_type = data.get('subscription_type')
        days = data.get('days')

        if subscription_type == 'premium' and not days:
            raise serializers.ValidationError({
                'days': '프리미엄 구독은 days 파라미터가 필요합니다. (30, 90, 180, 365 중 선택)'
            })

        return data
