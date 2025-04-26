from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


def user_avatar_path(instance, filename):
    """사용자 아바타 이미지 저장 경로"""
    import os
    import uuid
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('accounts/avatars', filename)


class User(AbstractUser):
    """커스텀 유저 모델"""
    pass


class Profile(models.Model):
    """유저 프로필 모델"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField("프로필 이미지", upload_to=user_avatar_path, blank=True, null=True)
    bio = models.TextField("자기소개", blank=True)
    website = models.URLField("웹사이트", blank=True)
    
    def __str__(self):
        return f"{self.user.username}의 프로필"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """유저 생성 시 프로필도 자동 생성"""
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """유저 저장 시 프로필도 저장"""
    instance.profile.save()