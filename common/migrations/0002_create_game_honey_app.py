# Generated manually for game_honey TossApp data migration

from django.db import migrations
from django.conf import settings


def create_game_honey_app(apps, schema_editor):
    """
    기존 settings.py의 게임 하니 설정을 TossApp으로 마이그레이션
    """
    TossApp = apps.get_model('common', 'TossApp')

    # 기존 settings에서 값 가져오기
    TossApp.objects.create(
        app_id='game_honey',
        display_name='게임 하니',
        toss_client_id='',  # settings에 없으면 빈 값
        toss_decrypt_key=getattr(settings, 'TOSS_DECRYPT_KEY', ''),
        toss_decrypt_aad=getattr(settings, 'TOSS_DECRYPT_AAD', 'TOSS'),
        cert_path=getattr(settings, 'TOSS_CERT_PATH', '') or getattr(settings, 'TOSS_MTLS_CERT_PATH', ''),
        key_path=getattr(settings, 'TOSS_KEY_PATH', '') or getattr(settings, 'TOSS_MTLS_KEY_PATH', ''),
        disconnect_callback_username=getattr(settings, 'TOSS_DISCONNECT_CALLBACK_USERNAME', 'gamehoney'),
        disconnect_callback_password=getattr(settings, 'TOSS_DISCONNECT_CALLBACK_PASSWORD', ''),
        is_active=True,
    )


def reverse_game_honey_app(apps, schema_editor):
    """
    롤백 시 게임 하니 앱 삭제
    """
    TossApp = apps.get_model('common', 'TossApp')
    TossApp.objects.filter(app_id='game_honey').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_game_honey_app, reverse_game_honey_app),
    ]
