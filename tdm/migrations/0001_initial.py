from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='PredictionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('login_id', models.CharField(blank=True, default='', max_length=64)),
                ('input_json', models.JSONField()),
                ('result_json', models.JSONField()),
                ('ml_model', models.CharField(blank=True, default='', max_length=32)),
                ('dl_model', models.CharField(blank=True, default='', max_length=32)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
