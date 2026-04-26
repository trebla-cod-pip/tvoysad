import hashlib
import random
import string
from urllib.parse import urlencode

from django.db import models
from django.utils import timezone


def _generate_code():
    chars = string.ascii_uppercase + string.digits
    for _ in range(100):
        code = ''.join(random.choices(chars, k=8))
        if not AdCampaign.objects.filter(code=code).exists():
            return code
    raise RuntimeError('Не удалось сгенерировать уникальный код')


class AdCampaign(models.Model):
    SOURCE_CHOICES = [
        ('vk',        'ВКонтакте'),
        ('instagram', 'Instagram'),
        ('telegram',  'Telegram'),
        ('facebook',  'Facebook'),
        ('yandex',    'Яндекс'),
        ('google',    'Google'),
        ('flyer',     'Флаер / листовка'),
        ('other',     'Другое'),
    ]
    MEDIUM_CHOICES = [
        ('cpc',    'Платная реклама (CPC)'),
        ('post',   'Пост'),
        ('story',  'Stories / Reels'),
        ('banner', 'Баннер'),
        ('qr',     'QR-код'),
        ('direct', 'Прямой трафик'),
        ('other',  'Другое'),
    ]

    name         = models.CharField('Название', max_length=200,
                                    help_text='Для себя, например: «ВК апрель — слива»')
    utm_source   = models.CharField('Источник', max_length=100, choices=SOURCE_CHOICES)
    utm_medium   = models.CharField('Тип трафика', max_length=100, choices=MEDIUM_CHOICES)
    utm_campaign = models.CharField('Кампания (utm_campaign)', max_length=100,
                                    help_text='Латиницей без пробелов, например: spring_sale')
    utm_content  = models.CharField('Содержание (utm_content)', max_length=100, blank=True,
                                    help_text='Необязательно — для A/B тестов')
    destination  = models.CharField('Куда вести', max_length=500, default='/',
                                    help_text='Путь на сайте: / или /catalog/ или /catalog/yablonia/')
    code         = models.CharField('Код ссылки', max_length=20, unique=True, blank=True,
                                    help_text='Генерируется автоматически')
    is_active    = models.BooleanField('Активна', default=True)
    created_at   = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Рекламная кампания'
        verbose_name_plural = 'Рекламные кампании'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = _generate_code()
        super().save(*args, **kwargs)

    def get_tracking_path(self):
        return f'/go/{self.code}/'

    def get_destination_with_utm(self):
        params = {'utm_source': self.utm_source,
                  'utm_medium': self.utm_medium,
                  'utm_campaign': self.utm_campaign}
        if self.utm_content:
            params['utm_content'] = self.utm_content
        sep = '&' if '?' in self.destination else '?'
        return f'{self.destination}{sep}{urlencode(params)}'

    # ── аннотируемые свойства (кэшируются через annotate в admin) ──────────
    def _clicks_since(self, days):
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.clicks.filter(timestamp__gte=cutoff).count()

    @property
    def total_clicks(self):
        return self.clicks.count()

    @property
    def clicks_7d(self):
        return self._clicks_since(7)

    @property
    def clicks_30d(self):
        return self._clicks_since(30)


class AdClick(models.Model):
    campaign   = models.ForeignKey(AdCampaign, on_delete=models.CASCADE,
                                   related_name='clicks', verbose_name='Кампания')
    timestamp  = models.DateTimeField('Время', auto_now_add=True, db_index=True)
    ip_hash    = models.CharField(max_length=16, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    referrer   = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = 'Клик'
        verbose_name_plural = 'Клики'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.campaign.name} — {self.timestamp:%d.%m.%Y %H:%M}'
