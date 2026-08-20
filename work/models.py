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


class WorkPost(models.Model):
    CATEGORY_CHOICES = [
        ('novel', '소설'),
        ('essay', '수필'),
        ('etc', '기타'),
    ]

    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, default='novel')
    title = models.CharField(max_length=200)
    author_name = models.CharField(max_length=32, default='익명')
    author_ip = models.GenericIPAddressField(null=True, blank=True)
    body = models.TextField(blank=True, default='')
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
