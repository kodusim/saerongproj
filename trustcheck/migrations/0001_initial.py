import django.db.models.deletion
from django.db import migrations, models


def seed_products(apps, schema_editor):
    Product = apps.get_model('trustcheck', 'Product')
    data = [
        ('A', 'PM 검수', '기획서·견적서를 IT PM이 검수합니다. 개발 범위와 금액의 적정성을 짚어드립니다.', 150000, False, 1),
        ('B', '변호사 검토', '계약서를 변호사가 검토합니다. 독소조항과 리스크를 법률 관점에서 확인합니다.', 200000, False, 2),
        ('C', 'PM + 변호사', 'PM 검수 결과를 변호사에게 전달해 순차 진행합니다. 기술·법률을 한 번에.', 320000, True, 3),
        ('PREMIUM', '분쟁 분석', '기능 구현율을 산출하고 법률 의견을 더합니다. 분쟁 대응 자료.', 500000, False, 4),
    ]
    for code, name, desc, price, seq, order in data:
        Product.objects.update_or_create(
            code=code,
            defaults={'name': name, 'description': desc, 'price': price,
                      'is_sequential': seq, 'order': order},
        )


def unseed_products(apps, schema_editor):
    apps.get_model('trustcheck', 'Product').objects.all().delete()


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='TCUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('password', models.CharField(max_length=128)),
                ('name', models.CharField(max_length=64)),
                ('role', models.CharField(choices=[('client', '발주자'), ('expert', '전문가'), ('admin', '관리자')], default='client', max_length=16)),
                ('expert_type', models.CharField(blank=True, choices=[('', '-'), ('pm', 'IT PM'), ('lawyer', '변호사')], default='', max_length=16)),
                ('is_approved', models.BooleanField(default=False)),
                ('bio', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=16, unique=True)),
                ('name', models.CharField(max_length=64)),
                ('description', models.TextField(blank=True, default='')),
                ('price', models.PositiveIntegerField(default=0)),
                ('is_sequential', models.BooleanField(default=False)),
                ('order', models.PositiveIntegerField(default=0)),
            ],
            options={'ordering': ['order']},
        ),
        migrations.CreateModel(
            name='ConsultPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('field', models.CharField(choices=[('pm', 'IT PM (기획·견적)'), ('lawyer', '법률 (계약)'), ('both', '융합 (기술+법률)'), ('dispute', '분쟁 분석')], default='pm', max_length=16)),
                ('situation', models.TextField(help_text='상황 설명')),
                ('budget', models.CharField(blank=True, default='', help_text='금액 규모', max_length=64)),
                ('status', models.CharField(choices=[('open', '모집중'), ('matched', '매칭됨'), ('closed', '종료')], default='open', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='trustcheck.tcuser')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='ExpertMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(help_text='어필 메시지')),
                ('status', models.CharField(choices=[('pending', '대기'), ('accepted', '수락'), ('rejected', '거절')], default='pending', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expert', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appeals', to='trustcheck.tcuser')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appeals', to='trustcheck.consultpost')),
            ],
            options={'ordering': ['-created_at'], 'unique_together': {('post', 'expert')}},
        ),
        migrations.CreateModel(
            name='ChatRoom',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('free_seconds', models.PositiveIntegerField(default=900)),
                ('is_closed', models.BooleanField(default=False)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='client_rooms', to='trustcheck.tcuser')),
                ('expert', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='expert_rooms', to='trustcheck.tcuser')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rooms', to='trustcheck.consultpost')),
            ],
            options={'ordering': ['-started_at']},
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField(blank=True, default='')),
                ('file', models.FileField(blank=True, null=True, upload_to='trustcheck/chat/')),
                ('is_system', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='trustcheck.chatroom')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to='trustcheck.tcuser')),
            ],
            options={'ordering': ['created_at']},
        ),
        migrations.CreateModel(
            name='Case',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stage', models.CharField(choices=[('paid', '결제완료'), ('materials', '자료전달'), ('reviewing', '검토중'), ('meeting', '화상상담예정'), ('pm_done', 'PM완료(변호사대기)'), ('reported', '리포트발행'), ('done', '완료')], default='paid', max_length=16)),
                ('inquiry', models.TextField(blank=True, default='', help_text='질의사항')),
                ('meet_url', models.URLField(blank=True, default='')),
                ('meet_at', models.DateTimeField(blank=True, null=True)),
                ('paid_amount', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cases', to='trustcheck.tcuser')),
                ('expert', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='expert_cases', to='trustcheck.tcuser')),
                ('lawyer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lawyer_cases', to='trustcheck.tcuser')),
                ('post', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cases', to='trustcheck.consultpost')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cases', to='trustcheck.product')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='CaseFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('contract', '계약서'), ('plan', '기획서'), ('quote', '견적서'), ('etc', '기타')], default='etc', max_length=16)),
                ('file', models.FileField(upload_to='trustcheck/cases/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='trustcheck.case')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='trustcheck.tcuser')),
            ],
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('summary', models.TextField(blank=True, default='')),
                ('body', models.TextField(blank=True, default='')),
                ('file', models.FileField(blank=True, null=True, upload_to='trustcheck/reports/')),
                ('signal', models.CharField(blank=True, choices=[('green', '안전'), ('amber', '주의'), ('red', '위험')], default='', max_length=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reports', to='trustcheck.tcuser')),
                ('case', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='trustcheck.case')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.RunPython(seed_products, unseed_products),
    ]
