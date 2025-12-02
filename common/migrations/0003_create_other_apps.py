# Generated manually for other TossApp data migration

from django.db import migrations


def create_other_apps(apps, schema_editor):
    """
    나머지 4개 앱 TossApp 레코드 생성

    실제 Toss API 설정 값은 나중에 Admin에서 입력해야 합니다.
    """
    TossApp = apps.get_model('common', 'TossApp')

    apps_to_create = [
        {
            'app_id': 'paljalog',
            'display_name': '팔자로그',
        },
        {
            'app_id': 'nongga',
            'display_name': '요즘농가',
        },
        {
            'app_id': 'amoa',
            'display_name': '아모아',
        },
        {
            'app_id': 'trend_moa',
            'display_name': '트렌드 모아',
        },
    ]

    for app_data in apps_to_create:
        TossApp.objects.get_or_create(
            app_id=app_data['app_id'],
            defaults={
                'display_name': app_data['display_name'],
                'is_active': False,  # 설정 완료 전까지 비활성화
            }
        )


def reverse_other_apps(apps, schema_editor):
    """
    롤백 시 생성된 앱들 삭제
    """
    TossApp = apps.get_model('common', 'TossApp')
    TossApp.objects.filter(app_id__in=['paljalog', 'nongga', 'amoa', 'trend_moa']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0002_create_game_honey_app'),
    ]

    operations = [
        migrations.RunPython(create_other_apps, reverse_other_apps),
    ]
