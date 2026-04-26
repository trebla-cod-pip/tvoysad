"""
Обновление цен согласно актуальному прайс-листу.

Использование:
    python manage.py update_prices          # применить
    python manage.py update_prices --dry-run  # только показать изменения
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from catalog.models import Product, ProductAgeVariant


# ---------------------------------------------------------------------------
# Правила обновления
# ---------------------------------------------------------------------------
# Каждая запись: (name_icontains, base_price, age_variants, deactivate)
#   name_icontains  — подстрока названия (без учёта регистра)
#   base_price      — новая базовая цена Product.price
#   age_variants    — список (лет, цена) для ProductAgeVariant, либо None
#   deactivate      — True = снять с продажи (is_active=False, stock=0)

RULES = [
    # ── Плодовые деревья: возрастные варианты 3л/4л/5л ─────────────────────
    ('Яблоня колоновидная', 2200, [(3, 2200), (4, 3000), (5, 3000)], False),
    ('Яблоня Роялти',       3000, None, False),   # декоративная — исключение
    ('Яблоня',              2200, [(3, 2200), (4, 3000), (5, 3000)], False),
    ('Груша колоновидная',  2200, [(3, 2200), (4, 3000), (5, 3000)], False),
    ('Груша',               2200, [(3, 2200), (4, 3000), (5, 3000)], False),
    ('Слива Писсарди',      3000, None, False),   # декоративная — исключение
    ('Слива колоновидная',  2200, [(3, 2200), (4, 3000), (5, 3000)], False),
    ('Слива чернослив',     2200, [(3, 2200), (4, 3000), (5, 3000)], False),
    ('Слива жёлтая',        2200, [(3, 2200), (4, 3000), (5, 3000)], False),
    ('Слива',               2200, [(3, 2200), (4, 3000), (5, 3000)], False),
    ('Вишня карликовая',    2200, [(3, 2200), (4, 3000), (5, 3000)], False),
    ('Вишня',               2200, [(3, 2200), (4, 3000), (5, 3000)], False),

    # ── Черешни: плоская цена 3000 (без возрастных вариантов) ───────────────
    ('Черешня Валерий Чкалов', 3000, None, False),
    ('Черешня Бычье сердце',   3000, None, False),
    ('Черешня Ревна',          3000, None, False),
    ('Черешня Ипуть',          3000, None, False),

    # ── Декоративные деревья ─────────────────────────────────────────────────
    ('Шелковица плакучая',         8000, None, False),
    ('Черёмуха Шуберта',           2200, None, False),
    ('Ива извилистая',             3000, None, False),
    ('Ива кудрявая',               3000, None, False),
    ('Сакура',                     3000, None, False),
    ('Миндаль цветущий',           3000, None, False),
    ('Сирень Красавица Москвы',    2500, [(4, 2500), (5, 5000)], False),
    ('Сирень Огни Москвы',         2500, [(4, 2500), (5, 5000)], False),
    ('Сирень Сумерки',             2500, [(4, 2500), (5, 5000)], False),
    ('Сирень Белая махровая',      2500, [(4, 2500), (5, 5000)], False),
    ('Сирень Сенсация',            2500, [(4, 2500), (5, 5000)], False),

    # ── Плодовые кустарники ─────────────────────────────────────────────────
    ('Клубника садовая',  120,  None, False),
    ('Ежевика садовая',   None, None, True),   # снять с продажи
    ('Малина',            1000, None, False),
    ('Голубика Патриот',  4000, None, False),
    ('Крыжовник',         700,  [(3, 700), (4, 1000)], False),
    ('Смородина чёрная',  700,  [(3, 700), (4, 1000)], False),
    ('Смородина красная', 700,  [(3, 700), (4, 1000)], False),

    # ── Декоративные кустарники ──────────────────────────────────────────────
    ('Вейгела',                 800,  [(3, 800), (5, 1500)], False),
    ('Спирея Голдфлейм',        1500, None, False),
    ('Спирея Грефшейм',         1500, None, False),
    ('Спирея Вангутта',         1500, None, False),
    ('Снежноягодник розовый',   1500, None, False),
    ('Снежноягодник белый',     1500, None, False),
    ('Пузыреплодник Диабло',    1300, None, False),
    ('Кизильник блестящий',     1000, None, False),
    ('Бобовник',                1000, None, False),
    ('Форзиция',                2500, None, False),
    ('Жасмин садовый',          1200, [(3, 1200), (5, 2000)], False),
]

# Подстроки в названиях, которые нужно убрать (старые обозначения возраста)
STRIP_FROM_NAMES = [
    ' (трехлетняя)',
    ' (трёхлетняя)',
    ' (пятилетняя)',
    ' (четырехлетняя)',
    ' (четырёхлетняя)',
    ' (двухлетняя)',
    ' (трехлетний)',
    ' (пятилетний)',
]


def clean_name(name: str) -> str:
    for suffix in STRIP_FROM_NAMES:
        name = name.replace(suffix, '').replace(suffix.lower(), '')
    return name.strip()


class Command(BaseCommand):
    help = 'Обновляет цены и возрастные варианты согласно актуальному прайс-листу'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать изменения без сохранения в БД',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== РЕЖИМ ПРОСМОТРА (dry-run) ===\n'))

        all_products = list(Product.objects.prefetch_related('age_variants').all())
        matched_ids = set()

        for name_pattern, base_price, age_variants, deactivate in RULES:
            # Ищем совпадение по подстроке, точнее — по вхождению без учёта регистра
            matches = [
                p for p in all_products
                if name_pattern.lower() in p.name.lower() and p.id not in matched_ids
            ]

            if not matches:
                self.stdout.write(
                    self.style.WARNING(f'  [не найдено] "{name_pattern}"')
                )
                continue

            for product in matches:
                matched_ids.add(product.id)
                changes = []

                # Очистка названия от старых обозначений возраста
                new_name = clean_name(product.name)
                if new_name != product.name:
                    changes.append(f'название: "{product.name}" → "{new_name}"')
                    if not dry_run:
                        product.name = new_name

                if deactivate:
                    if product.is_active or product.stock != 0:
                        changes.append('снят с продажи (is_active=False, stock=0)')
                        if not dry_run:
                            product.is_active = False
                            product.stock = 0
                else:
                    if base_price is not None and product.price != base_price:
                        changes.append(f'цена: {product.price} → {base_price} ₽')
                        if not dry_run:
                            product.price = base_price
                    # Убираем старую цену (она была в формате "2200 / 2500" как скидка)
                    if product.old_price is not None:
                        changes.append(f'старая цена убрана ({product.old_price} ₽)')
                        if not dry_run:
                            product.old_price = None

                if not dry_run:
                    product.save(update_fields=['name', 'price', 'old_price', 'is_active', 'stock'])

                # Возрастные варианты
                if age_variants and not deactivate:
                    existing = {v.age_years: v for v in product.age_variants.all()}
                    for age_years, price in age_variants:
                        if age_years in existing:
                            v = existing[age_years]
                            if v.price != price:
                                changes.append(f'вариант {age_years}л: {v.price} → {price} ₽')
                                if not dry_run:
                                    v.price = price
                                    v.save(update_fields=['price'])
                        else:
                            changes.append(f'новый вариант {age_years}л: {price} ₽')
                            if not dry_run:
                                ProductAgeVariant.objects.create(
                                    product=product,
                                    age_years=age_years,
                                    price=price,
                                    stock=product.stock,
                                )

                if changes:
                    label = self.style.SUCCESS('  ✓') if not dry_run else self.style.WARNING('  ~')
                    self.stdout.write(f'{label} {product.name}')
                    for c in changes:
                        self.stdout.write(f'      {c}')
                else:
                    self.stdout.write(f'  = {product.name} (без изменений)')

        # Отчёт о товарах, которых не затронули
        unmatched = [p for p in all_products if p.id not in matched_ids]
        if unmatched:
            self.stdout.write('\n' + self.style.WARNING('Товары без правила в прайс-листе:'))
            for p in unmatched:
                self.stdout.write(f'  - {p.name} ({p.price} ₽)')

        if dry_run:
            self.stdout.write(self.style.WARNING('\nИзменения НЕ сохранены. Уберите --dry-run для применения.'))
            transaction.set_rollback(True)
        else:
            self.stdout.write(self.style.SUCCESS('\nВсе цены обновлены.'))
