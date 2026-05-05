import json
import urllib.request

from django.core.management.base import BaseCommand

from catalog.models import Category, Product


class Command(BaseCommand):
    help = 'Выводит каталог товаров в формате для Telegram'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category', type=str, default='',
            help='Slug категории (по умолчанию все)',
        )
        parser.add_argument(
            '--send', action='store_true',
            help='Отправить сообщение в Telegram (использует настройки из SiteSettings)',
        )

    def handle(self, *args, **options):
        category_slug = options['category']

        categories = Category.objects.filter(is_active=True, parent=None).order_by('sort_order', 'name')
        if category_slug:
            categories = categories.filter(slug=category_slug)

        tg_blocks = []   # богатый HTML для Telegram
        plain_blocks = []  # plain text для консоли

        for category in categories:
            products = Product.objects.filter(
                is_active=True, category=category, stock__gt=0,
            ).prefetch_related('age_variants').order_by('name')

            if not products.exists():
                continue

            tg_lines = [f'<b>{category.name}</b>']
            plain_lines = [f'[ {category.name} ]']

            for product in products:
                variants = list(product.age_variants.all())
                if variants:
                    tg_lines.append(f'\n\U0001f331 <b>{product.name}</b>')
                    plain_lines.append(f'\n  {product.name}')
                    for v in variants:
                        price = f'{int(v.price):,}'.replace(',', ' ')
                        tg_lines.append(f'   {v.age_label} — {price} ₽')
                        plain_lines.append(f'   {v.age_label} - {price} руб.')
                else:
                    price = f'{int(product.price):,}'.replace(',', ' ')
                    if product.old_price and product.old_price > product.price:
                        old = f'{int(product.old_price):,}'.replace(',', ' ')
                        tg_lines.append(
                            f'\U0001f331 <b>{product.name}</b> — {price} ₽ <s>{old} ₽</s>'
                        )
                        plain_lines.append(f'  {product.name} - {price} руб. (было {old} руб.)')
                    else:
                        tg_lines.append(f'\U0001f331 <b>{product.name}</b> — {price} ₽')
                        plain_lines.append(f'  {product.name} - {price} руб.')

            tg_blocks.append('\n'.join(tg_lines))
            plain_blocks.append('\n'.join(plain_lines))

        if not tg_blocks:
            self.stderr.write('Нет активных товаров в наличии.')
            return

        plain_text = '\n\n'.join(plain_blocks)
        tg_text = '\n\n'.join(tg_blocks)

        # Выводим в консоль без эмодзи
        self.stdout.write(plain_text)

        if options['send']:
            self._send(tg_text)

    def _send(self, text):
        from pages.models import SiteSettings

        s = SiteSettings.get()
        token = s.tg_bot_token.strip()
        chat_id = s.tg_admin_chat_id.strip()
        proxy_url = s.tg_proxy_url.strip()

        if not token or not chat_id:
            self.stderr.write('Не заданы tg_bot_token или tg_admin_chat_id в настройках.')
            return

        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({'https': proxy_url, 'http': proxy_url})
        ) if proxy_url else urllib.request.build_opener()

        # Telegram ограничивает сообщение 4096 символами — режем на части
        chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
        for i, chunk in enumerate(chunks, 1):
            payload = json.dumps({
                'chat_id': chat_id,
                'text': chunk,
                'parse_mode': 'HTML',
            }).encode()
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{token}/sendMessage',
                data=payload,
                headers={'Content-Type': 'application/json'},
            )
            try:
                resp = opener.open(req, timeout=10)
                data = json.loads(resp.read())
                if data.get('ok'):
                    self.stdout.write(self.style.SUCCESS(f'Часть {i}/{len(chunks)} отправлена.'))
                else:
                    self.stderr.write(f'Ошибка Telegram: {data}')
            except Exception as e:
                self.stderr.write(f'Ошибка отправки: {e}')
