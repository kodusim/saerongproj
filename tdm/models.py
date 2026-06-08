from django.db import models


class PredictionLog(models.Model):
    """예측 요청 로그 (감사/통계용)."""
    created_at = models.DateTimeField(auto_now_add=True)
    login_id = models.CharField(max_length=64, blank=True, default='')
    input_json = models.JSONField()
    result_json = models.JSONField()
    ml_model = models.CharField(max_length=32, blank=True, default='')
    dl_model = models.CharField(max_length=32, blank=True, default='')

    class Meta:
        ordering = ['-created_at']
