from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('work', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workchatmessage',
            name='body',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='workchatmessage',
            name='sender_ip',
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='workchatmessage',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='work/chat/%Y/%m/'),
        ),
    ]
