from django.db import models


class ActivityLog(models.Model):
    EVENT_PAGEVIEW = 'pageview'
    EVENT_API      = 'api'
    EVENT_AUTH     = 'auth'
    EVENT_FORM     = 'form'
    EVENT_ERROR    = 'error'
    EVENT_OTHER    = 'other'

    EVENT_CHOICES = [
        (EVENT_PAGEVIEW, 'Просмотр страницы'),
        (EVENT_API,      'API-запрос'),
        (EVENT_AUTH,     'Авторизация / выход'),
        (EVENT_FORM,     'Отправка формы'),
        (EVENT_ERROR,    'Ошибка'),
        (EVENT_OTHER,    'Другое'),
    ]

    # Идентификация посетителя
    uid         = models.CharField('UID посетителя', max_length=32, db_index=True)
    session_key = models.CharField('Session key', max_length=40, blank=True)
    ip_address  = models.GenericIPAddressField('IP-адрес', null=True, blank=True)

    # Время
    timestamp = models.DateTimeField('Время (UTC)', db_index=True)

    # Запрос
    method       = models.CharField('HTTP метод', max_length=10)
    path         = models.CharField('Путь', max_length=2000, db_index=True)
    query_string = models.TextField('Query string', blank=True)

    # Ответ
    status_code      = models.PositiveSmallIntegerField('Статус-код', db_index=True)
    response_time_ms = models.PositiveIntegerField('Время ответа (мс)')

    # Заголовки браузера
    referrer   = models.TextField('Referrer', blank=True)
    user_agent = models.TextField('User-Agent', blank=True)

    # Тип события
    event_type = models.CharField(
        'Тип события', max_length=20,
        choices=EVENT_CHOICES, default=EVENT_PAGEVIEW,
        db_index=True,
    )

    # Источник трафика
    SOURCE_TG  = 'telegram'
    SOURCE_WEB = 'web'
    SOURCE_CHOICES = [
        (SOURCE_TG,  'Telegram'),
        (SOURCE_WEB, 'Веб'),
    ]
    source = models.CharField(
        'Источник', max_length=20,
        choices=SOURCE_CHOICES, default=SOURCE_WEB,
        db_index=True,
    )

    # Авторизованный пользователь (если есть)
    user_id = models.IntegerField('ID пользователя', null=True, blank=True, db_index=True)

    class Meta:
        verbose_name        = 'Лог активности'
        verbose_name_plural = 'Логи активности'
        ordering            = ['-timestamp']
        indexes = [
            models.Index(fields=['uid', 'timestamp'],        name='activity_uid_ts'),
            models.Index(fields=['path', 'status_code'],     name='activity_path_status'),
            models.Index(fields=['event_type', 'timestamp'], name='activity_evt_ts'),
        ]

    def __str__(self):
        return f'[{self.event_type}] {self.method} {self.path} {self.status_code} ({self.uid})'
