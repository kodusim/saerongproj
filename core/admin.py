from django.contrib import admin
from .models import Category, SubCategory
from sources.models import DataSource


class DataSourceInline(admin.TabularInline):
    """중분류(SubCategory)에 소분류(DataSource) 인라인 추가"""
    model = DataSource
    extra = 3  # 기본으로 3개 빈 폼 제공
    fields = ['name', 'url', 'crawler_type', 'crawler_class', 'crawl_interval', 'is_active']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'is_active', 'order', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'is_active', 'order', 'created_at']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['category', 'order', 'name']
    inlines = [DataSourceInline]  # 소분류 한 번에 추가
