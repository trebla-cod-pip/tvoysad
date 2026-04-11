"""
python manage.py generate_webp [--force]

Re-generates WebP thumbnails for all Category and Product images.
Use --force to regenerate even if thumbs already exist.
"""
from django.core.management.base import BaseCommand

from catalog.image_utils import generate_webp_thumbs, THUMB_WIDTHS
from catalog.models import Category, Product, ProductImage


class Command(BaseCommand):
    help = 'Generate WebP thumbnails for all Category and Product images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Overwrite existing thumbnails',
        )

    def handle(self, *args, **options):
        force = options['force']
        total = ok = skipped = err = 0

        def process(label, image_name):
            nonlocal total, ok, skipped, err
            if not image_name:
                return
            total += 1
            result = generate_webp_thumbs(image_name, force=force)
            if result:
                ok += 1
                self.stdout.write(f'  OK  {label}')
            elif not force:
                skipped += 1
            else:
                err += 1
                self.stderr.write(f'  ERR {label}')

        self.stdout.write('→ Categories...')
        for cat in Category.objects.exclude(image=''):
            process(f'Category({cat.pk}) {cat.name}', cat.image.name)

        self.stdout.write('→ Products...')
        for prod in Product.objects.exclude(image=''):
            process(f'Product({prod.pk}) {prod.name}', prod.image.name)

        self.stdout.write('→ Product gallery...')
        for pi in ProductImage.objects.all():
            process(f'ProductImage({pi.pk}) {pi.product.name}', pi.image.name)

        self.stdout.write(self.style.SUCCESS(
            f'\nDone: {ok} generated, {skipped} skipped (already exist), {err} errors'
            f' | widths: {THUMB_WIDTHS}'
        ))
