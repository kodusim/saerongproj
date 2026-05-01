from django.db import migrations


SEED = [
    ('equip', [
        '희귀 목걸이', '영웅 목걸이', '영웅 귀걸이', '영웅 팔찌', '영웅 반지',
        '영웅 허리띠', '영웅 무기', '영웅 망토', '스킬북', '전설 하의(판금)',
    ]),
    ('mount', [
        '델폰', '리버티', '램폰', '드라카스', '페르톨로프', '언데믹', '라바토니스', '글레이시스',
    ]),
    ('special', [
        '베나투스', '비오렌트', '클레멘티스', '에고', '리베라', '아라네오', '사피루스',
        '언두미엘', '네우트로', '레이디달리아', '튀멜레', '장군 아쿨레우스', '아멘티스',
        '남작 브라우드모어', '밀라베', '와니타스', '메투스', '두플리칸', '링고르',
        '슈라이어', '로데릭', '가레스', '티토르', '라르바', '아우라크', '카테나',
        '세크레타', '오르도', '아스타', '수포르', '샤이프락', '벤지', '리비티나',
        '라카제스', '카말리아', '익시온', '투미어',
    ]),
]


def seed(apps, schema_editor):
    EquipSlot = apps.get_model('animal', 'EquipSlot')
    for section, names in SEED:
        for i, name in enumerate(names, start=1):
            EquipSlot.objects.get_or_create(
                section=section,
                name=name,
                defaults={'order': i},
            )


def unseed(apps, schema_editor):
    EquipSlot = apps.get_model('animal', 'EquipSlot')
    EquipSlot.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('animal', '0005_equip'),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]
