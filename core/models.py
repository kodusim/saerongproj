from django.db import models

def banner_image_path(instance, filename):
    """배너 이미지 저장 경로"""
    import os
    import uuid
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('banners', filename)

class Banner(models.Model):
    """메인 페이지 배너 이미지 모델"""
    title = models.CharField("제목", max_length=100)
    image = models.ImageField("배너 이미지", upload_to=banner_image_path)
    url = models.URLField("링크 URL", blank=True)
    is_active = models.BooleanField("활성화", default=True)
    order = models.PositiveIntegerField("순서", default=0)
    created_at = models.DateTimeField("등록일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "배너"
        verbose_name_plural = "배너 관리"
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title