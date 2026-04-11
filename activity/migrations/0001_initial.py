from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id',               models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uid',              models.CharField(db_index=True, max_length=32, verbose_name='UID посетителя')),
                ('session_key',      models.CharField(blank=True, max_length=40, verbose_name='Session key')),
                ('ip_address',       models.GenericIPAddressField(blank=True, null=True, verbose_name='IP-адрес')),
                ('timestamp',        models.DateTimeField(db_index=True, verbose_name='Время (UTC)')),
                ('method',           models.CharField(max_length=10, verbose_name='HTTP метод')),
                ('path',             models.CharField(db_index=True, max_length=2000, verbose_name='Путь')),
                ('query_string',     models.TextField(blank=True, verbose_name='Query string')),
                ('status_code',      models.PositiveSmallIntegerField(db_index=True, verbose_name='Статус-код')),
                ('response_time_ms', models.PositiveIntegerField(verbose_name='Время ответа (мс)')),
                ('referrer',         models.TextField(blank=True, verbose_name='Referrer')),
                ('user_agent',       models.TextField(blank=True, verbose_name='User-Agent')),
                ('event_type',       models.CharField(
                    choices=[
                        ('pageview', 'Просмотр страницы'),
                        ('api',      'API-запрос'),
                        ('auth',     'Авторизация / выход'),
                        ('form',     'Отправка формы'),
                        ('error',    'Ошибка'),
                        ('other',    'Другое'),
                    ],
                    db_index=True, default='pageview', max_length=20,
                    verbose_name='Тип события',
                )),
                ('user_id', models.IntegerField(blank=True, db_index=True, null=True, verbose_name='ID пользователя')),
            ],
            options={
                'verbose_name':        'Лог активности',
                'verbose_name_plural': 'Логи активности',
                'ordering':            ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='activitylog',
            index=models.Index(fields=['uid', 'timestamp'], name='activity_uid_ts'),
        ),
        migrations.AddIndex(
            model_name='activitylog',
            index=models.Index(fields=['path', 'status_code'], name='activity_path_status'),
        ),
        migrations.AddIndex(
            model_name='activitylog',
            index=models.Index(fields=['event_type', 'timestamp'], name='activity_evt_ts'),
        ),
    ]
