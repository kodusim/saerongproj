from django.db import migrations


INITIAL_NICKNAMES = [
    '표범', '빈투', '대악마', '퍼그', '해파리', '강치', '흑여우', '맹수',
    '흰담비', '졸귀', '시뱌', '와닥', '해마', '백상어', '바다거북', '말레이곰',
    'Mr리', '요크셔테리어', '얼룩말', '코요테', '항공', '지하철', '쿠궁', '거미',
    '이구아나', '라쿤', '태양곰', '참수리',
]


def seed(apps, schema_editor):
    GuildMember = apps.get_model('animal', 'GuildMember')
    for i, nick in enumerate(INITIAL_NICKNAMES, start=1):
        GuildMember.objects.get_or_create(
            nickname=nick,
            defaults={
                'power': 0,
                'weapon': '',
                'order': i,
                'active': True,
            },
        )


def unseed(apps, schema_editor):
    GuildMember = apps.get_model('animal', 'GuildMember')
    GuildMember.objects.filter(nickname__in=INITIAL_NICKNAMES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('animal', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]
