from django.db import models


class TelegramUser(models.Model):
    tg_id = models.BigIntegerField('Telegram ID', unique=True, db_index=True)
    username = models.CharField('Username', max_length=100, blank=True)
    first_name = models.CharField('Имя', max_length=100, blank=True)
    last_name = models.CharField('Фамилия', max_length=100, blank=True)
    language_code = models.CharField('Язык', max_length=10, blank=True)
    is_premium = models.BooleanField('Premium', default=False)
    allows_write_to_pm = models.BooleanField('Разрешил ЛС', default=False)
    photo_url = models.URLField('Фото', blank=True)
    platform = models.CharField('Платформа', max_length=50, blank=True)  # ios, android, web
    tg_version = models.CharField('Версия TG', max_length=20, blank=True)
    client_platform = models.CharField('Клиент', max_length=100, blank=True)
    visits_count = models.PositiveIntegerField('Визитов', default=0)
    created_at = models.DateTimeField('Первый визит', auto_now_add=True)
    last_seen = models.DateTimeField('Последний визит', auto_now=True)

    class Meta:
        verbose_name = 'Telegram пользователь'
        verbose_name_plural = 'Telegram пользователи'
        ordering = ['-last_seen']

    def __str__(self):
        name = self.first_name
        if self.last_name:
            name += f' {self.last_name}'
        if self.username:
            name += f' (@{self.username})'
        return name or f'tg:{self.tg_id}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def tg_link(self):
        if self.username:
            return f'https://t.me/{self.username}'
        return None


class TelegramVisit(models.Model):
    user = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE,
        related_name='visits', verbose_name='Пользователь'
    )
    page = models.CharField('Страница', max_length=500)
    platform = models.CharField('Платформа TG', max_length=50, blank=True)
    screen_width = models.PositiveSmallIntegerField('Ширина экрана', null=True, blank=True)
    screen_height = models.PositiveSmallIntegerField('Высота экрана', null=True, blank=True)
    user_agent = models.CharField('User-Agent', max_length=500, blank=True)
    theme = models.CharField('Тема', max_length=10, blank=True)  # light / dark
    created_at = models.DateTimeField('Время', auto_now_add=True)

    class Meta:
        verbose_name = 'Визит'
        verbose_name_plural = 'Визиты'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} — {self.page} ({self.created_at:%d.%m.%Y %H:%M})'
