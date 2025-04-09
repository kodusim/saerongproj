from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Test, Question, Option, Result

class OptionInline(admin.TabularInline):
    model = Option
    extra = 3

class QuestionAdmin(admin.ModelAdmin):
    inlines = [OptionInline]
    list_display = ['text', 'test', 'order']
    list_filter = ['test']
    search_fields = ['text']

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True

class ResultInline(admin.TabularInline):
    model = Result
    extra = 1

class TestAdmin(admin.ModelAdmin):
    inlines = [QuestionInline, ResultInline]
    list_display = ['title', 'category', 'created_at', 'calculation_method', 'view_style', 'show_thumbnail']
    list_filter = ['category', 'calculation_method', 'view_style']
    search_fields = ['title', 'description']
    readonly_fields = ['image_preview', 'intro_image_preview']
    
    def show_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No Image"
    show_thumbnail.short_description = '썸네일'
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" />', obj.image.url)
        return "No Image"
    image_preview.short_description = '썸네일 미리보기'
    
    def intro_image_preview(self, obj):
        if obj.intro_image:
            return format_html('<img src="{}" width="300" />', obj.intro_image.url)
        return "No Image"
    intro_image_preview.short_description = '인트로 이미지 미리보기'
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'category', 'calculation_method', 'view_style')
        }),
        ('이미지', {
            'fields': ('image', 'image_preview', 'intro_image', 'intro_image_preview'),
        }),
        ('통계', {
            'fields': ('view_count',),
        }),
    )

admin.site.register(Category)
admin.site.register(Test, TestAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Result)