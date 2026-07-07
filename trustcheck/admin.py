from django.contrib import admin
from .models import (
    TCUser, ConsultPost, ExpertMessage, ChatRoom, ChatMessage,
    Product, Case, CaseFile, Report,
)


@admin.register(TCUser)
class TCUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'role', 'expert_type', 'is_approved', 'created_at')
    list_filter = ('role', 'expert_type', 'is_approved')
    search_fields = ('name', 'email')


@admin.register(ConsultPost)
class ConsultPostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'field', 'status', 'created_at')
    list_filter = ('field', 'status')


@admin.register(ExpertMessage)
class ExpertMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'expert', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'price', 'is_sequential', 'order')


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'client', 'expert', 'lawyer', 'stage', 'created_at')
    list_filter = ('stage', 'product')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'case', 'author', 'signal', 'created_at')


admin.site.register(ChatRoom)
admin.site.register(ChatMessage)
admin.site.register(CaseFile)
