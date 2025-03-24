from django.contrib import admin
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
    list_display = ['title', 'category', 'created_at', 'calculation_method', 'view_style']
    list_filter = ['category', 'calculation_method', 'view_style']
    search_fields = ['title', 'description']

admin.site.register(Category)
admin.site.register(Test, TestAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Result)