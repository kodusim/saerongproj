from django.db import models


class WorkChatMessage(models.Model):
    sender_name = models.CharField(max_length=32, default='익명')
    sender_ip = models.GenericIPAddressField(null=True, blank=True)
    body = models.TextField(blank=True, default='')
    image = models.ImageField(upload_to='work/chat/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender_name}: {self.body[:20]}'
