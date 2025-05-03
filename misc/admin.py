from django.contrib import admin
from .models import FortuneType, FortuneCategory, FortuneContent, UserFortune, UserFortuneResult

class FortuneCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name']

class FortuneTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active', 'is_ready']
    list_editable = ['order', 'is_active', 'is_ready']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

class FortuneContentAdmin(admin.ModelAdmin):
    list_display = ['fortune_type', 'category', 'level', 'short_content', 'is_active']
    list_filter = ['fortune_type', 'category', 'level', 'is_active']
    search_fields = ['content', 'advice']
    list_editable = ['is_active']
    
    def short_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    short_content.short_description = '내용 미리보기'

admin.site.register(FortuneType, FortuneTypeAdmin)
admin.site.register(FortuneCategory, FortuneCategoryAdmin)
admin.site.register(FortuneContent, FortuneContentAdmin)
admin.site.register(UserFortune)
admin.site.register(UserFortuneResult)