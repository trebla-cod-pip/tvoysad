from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalog'
    verbose_name = 'Каталог'

    def ready(self):
        from django.db.models.signals import post_save
        from catalog.models import Category, Product, ProductImage
        from catalog.image_utils import generate_webp_async

        def _on_save(sender, instance, field='image', **kwargs):
            img = getattr(instance, field, None)
            if img and img.name:
                generate_webp_async(img.name)

        post_save.connect(_on_save, sender=Category,     dispatch_uid='cat_webp')
        post_save.connect(_on_save, sender=Product,      dispatch_uid='prod_webp')
        post_save.connect(_on_save, sender=ProductImage, dispatch_uid='pimg_webp')
