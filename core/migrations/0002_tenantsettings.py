# Generated manually for TenantSettings model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TenantSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ai_enabled', models.BooleanField(default=False)),
                ('ai_system_prompt', models.TextField(default='You are a helpful assistant that improves task descriptions. Keep responses clear and concise.', max_length=500)),
                ('ai_default_mode', models.CharField(choices=[('fix', 'Fix Language'), ('translate', 'Translate')], default='fix', max_length=20)),
                ('ai_default_language', models.CharField(choices=[('en', 'English'), ('tr', 'Turkish'), ('de', 'German'), ('fr', 'French'), ('es', 'Spanish')], default='en', max_length=5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='settings', to='core.tenant')),
            ],
            options={
                'db_table': 'tenant_settings',
            },
        ),
    ]
