from django.contrib import admin
from .models import PredictionLog


@admin.register(PredictionLog)
class PredictionLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'login_id', 'ml_model', 'dl_model')
    list_filter = ('ml_model', 'dl_model')
    search_fields = ('login_id',)
    readonly_fields = ('created_at', 'login_id', 'input_json', 'result_json', 'ml_model', 'dl_model')
