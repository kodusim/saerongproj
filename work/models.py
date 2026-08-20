from django.db import models


class WorkChatMessage(models.Model):
    sender_name = models.CharField(max_length=32, default='익명')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender_name}: {self.body[:20]}'
