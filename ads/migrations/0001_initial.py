from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AdCampaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Для себя, например: «ВК апрель — слива»', max_length=200, verbose_name='Название')),
                ('utm_source', models.CharField(choices=[('vk', 'ВКонтакте'), ('instagram', 'Instagram'), ('telegram', 'Telegram'), ('facebook', 'Facebook'), ('yandex', 'Яндекс'), ('google', 'Google'), ('flyer', 'Флаер / листовка'), ('other', 'Другое')], max_length=100, verbose_name='Источник')),
                ('utm_medium', models.CharField(choices=[('cpc', 'Платная реклама (CPC)'), ('post', 'Пост'), ('story', 'Stories / Reels'), ('banner', 'Баннер'), ('qr', 'QR-код'), ('direct', 'Прямой трафик'), ('other', 'Другое')], max_length=100, verbose_name='Тип трафика')),
                ('utm_campaign', models.CharField(help_text='Латиницей без пробелов, например: spring_sale', max_length=100, verbose_name='Кампания (utm_campaign)')),
                ('utm_content', models.CharField(blank=True, help_text='Необязательно — для A/B тестов', max_length=100, verbose_name='Содержание (utm_content)')),
                ('destination', models.CharField(default='/', help_text='Путь на сайте: / или /catalog/ или /catalog/yablonia/', max_length=500, verbose_name='Куда вести')),
                ('code', models.CharField(blank=True, help_text='Генерируется автоматически', max_length=20, unique=True, verbose_name='Код ссылки')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
            ],
            options={
                'verbose_name': 'Рекламная кампания',
                'verbose_name_plural': 'Рекламные кампании',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AdClick',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Время')),
                ('ip_hash', models.CharField(blank=True, max_length=16)),
                ('user_agent', models.CharField(blank=True, max_length=300)),
                ('referrer', models.CharField(blank=True, max_length=500)),
                ('campaign', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clicks', to='ads.adcampaign', verbose_name='Кампания')),
            ],
            options={
                'verbose_name': 'Клик',
                'verbose_name_plural': 'Клики',
                'ordering': ['-timestamp'],
            },
        ),
    ]
