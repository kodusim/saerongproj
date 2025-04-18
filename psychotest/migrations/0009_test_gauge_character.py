# Generated by Django 4.2.20 on 2025-04-18 15:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("psychotest", "0008_remove_sharedtestresult_image_question_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="test",
            name="gauge_character",
            field=models.ImageField(
                blank=True,
                help_text="권장 크기: 30x30px, 게이지 바에 표시될 캐릭터",
                null=True,
                upload_to="gauge_characters/",
                verbose_name="게이지 캐릭터 이미지",
            ),
        ),
    ]
