from django.db import models
from catalog.models import Product


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    name = models.CharField('Имя', max_length=100)
    rating = models.PositiveIntegerField('Оценка', default=5)
    text = models.TextField('Текст отзыва')
    is_approved = models.BooleanField('Одобрен', default=False)
    created_at = models.DateTimeField('Дата', auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.product.name} ({self.rating}★)'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._update_product_rating()

    def _update_product_rating(self):
        from django.db.models import Avg, Count
        stats = Review.objects.filter(
            product=self.product, is_approved=True
        ).aggregate(avg=Avg('rating'), cnt=Count('id'))
        self.product.rating = stats['avg'] or 0
        self.product.rating_count = stats['cnt'] or 0
        self.product.save(update_fields=['rating', 'rating_count'])


class Favorite(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorites')
    session_id = models.CharField('Session ID', max_length=100, db_index=True)
    created_at = models.DateTimeField('Добавлено', auto_now_add=True)

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        unique_together = [('product', 'session_id')]

    def __str__(self):
        return f'{self.product.name} ({self.session_id[:8]})'
