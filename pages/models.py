from django.db import models


class SiteSettings(models.Model):
    hero_image = models.ImageField('Hero-изображение', upload_to='site/', blank=True)

    phone = models.CharField('Телефон (основной)', max_length=50, default='+7 (999) 123-45-67')
    phone_delivery = models.CharField('Телефон (доставка)', max_length=50, default='+7 (999) 987-65-43', blank=True)
    email = models.EmailField('Email', default='hello@tvoysad.ru')
    schedule = models.CharField('График работы', max_length=100, default='Ежедневно: 9:00–20:00')
    address = models.CharField('Адрес питомника', max_length=200, default='Московская область, г. Сергиев Посад', blank=True)

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def __str__(self):
        return 'Настройки сайта'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Page(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField('Slug', unique=True)
    content = models.TextField('Содержимое (HTML)')
    is_published = models.BooleanField('Опубликована', default=True)
    meta_title = models.CharField('Meta title', max_length=200, blank=True)
    meta_description = models.TextField('Meta description', blank=True)

    class Meta:
        verbose_name = 'Страница'
        verbose_name_plural = 'Страницы'

    def __str__(self):
        return self.title


class ContactMessage(models.Model):
    name = models.CharField('Имя', max_length=100)
    contact = models.CharField('Email или телефон', max_length=200)
    message = models.TextField('Сообщение')
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField('Дата', auto_now_add=True)

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.created_at:%d.%m.%Y}'
