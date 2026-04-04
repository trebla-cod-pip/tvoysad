from django.db import models
from catalog.models import Product


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждён'),
        ('assembling', 'Комплектуется'),
        ('delivering', 'Доставляется'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменён'),
    ]
    PAYMENT_STATUS = [
        ('unpaid', 'Не оплачен'),
        ('paid', 'Оплачен'),
        ('refunded', 'Возвращён'),
    ]
    PAYMENT_METHOD = [
        ('card', 'Карта'),
        ('sbp', 'СБП'),
        ('cash', 'Наличные'),
    ]

    name = models.CharField('Имя', max_length=200)
    phone = models.CharField('Телефон', max_length=25)
    email = models.EmailField('Email', blank=True)
    delivery_address = models.TextField('Адрес доставки')
    delivery_date = models.DateField('Дата доставки', null=True, blank=True)
    delivery_time = models.CharField('Время доставки', max_length=50, blank=True)
    comment = models.TextField('Комментарий', blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField('Статус оплаты', max_length=20, choices=PAYMENT_STATUS, default='unpaid')
    payment_method = models.CharField('Способ оплаты', max_length=20, choices=PAYMENT_METHOD, default='card')
    tracking_number = models.CharField('Трек-номер', max_length=100, blank=True)
    total_amount = models.DecimalField('Сумма', max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заказ #{self.id} — {self.name}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField('Количество', default=1)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self):
        return f'{self.product} × {self.quantity}'

    @property
    def subtotal(self):
        return self.price * self.quantity
