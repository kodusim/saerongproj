from django.contrib import admin
from .models import BoardCategory, Post

@admin.register(BoardCategory)
class BoardCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ['is_active']
    search_fields = ['name', 'description']

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'author', 'view_count', 'is_notice', 'created_at']
    list_filter = ['category', 'is_notice', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['view_count']
    date_hierarchy = 'created_at'