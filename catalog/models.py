from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField('Название', max_length=100)
    slug = models.SlugField('Slug', unique=True, max_length=100)
    description = models.TextField('Описание', blank=True)
    image = models.ImageField('Изображение', upload_to='categories/', blank=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='children', verbose_name='Родительская категория'
    )
    is_active = models.BooleanField('Активна', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    created_at = models.DateTimeField('Создана', auto_now_add=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def get_products_count(self):
        return self.products.filter(is_active=True).count()


class Product(models.Model):
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('Slug', unique=True, max_length=200)
    description = models.TextField('Описание', blank=True)
    care_tips = models.TextField('Советы по уходу', blank=True)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    old_price = models.DecimalField('Старая цена', max_digits=10, decimal_places=2, null=True, blank=True)
    sku = models.CharField('Артикул', max_length=50, blank=True)
    unit = models.CharField('Единица', max_length=20, default='шт')
    rating = models.DecimalField('Рейтинг', max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField('Количество отзывов', default=0)
    image = models.ImageField('Основное изображение', upload_to='products/', blank=True)
    cart_image = models.ImageField('Миниатюра', upload_to='products/cart/', blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='products', verbose_name='Категория'
    )
    tags = models.CharField('Теги', max_length=200, blank=True, help_text='Через запятую: hit,new,sale')
    is_active = models.BooleanField('Активен', default=True)
    is_featured = models.BooleanField('Рекомендуемый', default=False)
    stock = models.PositiveIntegerField('Остаток', default=100)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int((1 - self.price / self.old_price) * 100)
        return 0

    def has_tag(self, tag):
        return tag in [t.strip() for t in self.tags.split(',')]

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        if img:
            return img
        return self.images.first()


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField('Изображение', upload_to='products/gallery/')
    alt_text = models.CharField('Alt-текст', max_length=200, blank=True)
    is_primary = models.BooleanField('Основное', default=False)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товара'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f'{self.product.name} — фото {self.id}'


class ProductSpecification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    key = models.CharField('Ключ', max_length=50)
    label = models.CharField('Название', max_length=100)
    value = models.CharField('Значение', max_length=200)
    icon = models.CharField('Иконка', max_length=50, default='leaf')
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Характеристика'
        verbose_name_plural = 'Характеристики'
        ordering = ['sort_order']

    def __str__(self):
        return f'{self.label}: {self.value}'
