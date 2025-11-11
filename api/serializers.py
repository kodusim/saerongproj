from rest_framework import serializers
from core.models import Category, SubCategory
from sources.models import DataSource
from collector.models import CollectedData, CrawlLog


class CategorySerializer(serializers.ModelSerializer):
    """카테고리 Serializer"""

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'is_active', 'order', 'created_at']


class SubCategorySerializer(serializers.ModelSerializer):
    """서브카테고리 Serializer"""
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = SubCategory
        fields = ['id', 'category', 'category_name', 'name', 'slug', 'is_active', 'created_at']


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
