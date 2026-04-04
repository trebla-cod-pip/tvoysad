#!/usr/bin/env python
"""
Скрипт заполнения демо-данными.
Запуск: python seed_data.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from catalog.models import Category, Product, ProductSpecification

# ── Categories ─────────────────────────────────────────────────────────────
cats_data = [
    ('Яблони', 'yabloni', '🍎', 'Плодовые яблони различных сортов'),
    ('Груши', 'grushi', '🍐', 'Сочные груши для вашего сада'),
    ('Сливы', 'slivy', '🫐', 'Сладкие и кисло-сладкие сливы'),
    ('Вишни', 'vishni', '🍒', 'Вишни и черешни'),
    ('Декоративные', 'dekorativnye', '🌸', 'Декоративные кустарники и деревья'),
]

categories = {}
for name, slug, emoji, desc in cats_data:
    cat, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name, 'description': desc})
    categories[slug] = cat
    print(f'  Категория: {name}')

# ── Products ───────────────────────────────────────────────────────────────
products_data = [
    {
        'name': 'Яблоня «Антоновка»',
        'slug': 'yablonya-antonovka',
        'category': 'yabloni',
        'price': 1200,
        'old_price': 1500,
        'tags': 'hit',
        'is_featured': True,
        'rating': 4.8,
        'rating_count': 12,
        'description': 'Классический русский зимний сорт с крупными плодами. Отличается высокой урожайностью и зимостойкостью.',
        'care_tips': 'Посадка: выберите солнечное место с хорошо дренированной почвой.\nПолив: 2–3 раза в неделю в первый год после посадки.\nОбрезка: формирующая обрезка ранней весной до распускания почек.\nУдобрение: весной азотные удобрения, летом — фосфорно-калийные.',
        'specs': [
            ('Сорт', 'Зимний', 'snowflake'),
            ('Высота', '3–4 м', 'ruler'),
            ('Морозостойкость', 'до −35°C', 'thermometer'),
            ('Освещённость', 'Полное солнце', 'sun'),
            ('Полив', 'Умеренный', 'droplets'),
        ],
    },
    {
        'name': 'Яблоня «Голден Делишес»',
        'slug': 'yablonya-golden',
        'category': 'yabloni',
        'price': 1400,
        'tags': 'new',
        'is_featured': True,
        'rating': 4.6,
        'rating_count': 8,
        'description': 'Популярный американский сорт с золотистыми сладкими плодами. Идеален для свежего потребления.',
        'care_tips': 'Любит солнечные, защищённые от ветра места. Требует опылителя.',
        'specs': [
            ('Сорт', 'Летний', 'sun'),
            ('Высота', '2.5–3.5 м', 'ruler'),
            ('Урожайность', 'Высокая', 'leaf'),
        ],
    },
    {
        'name': 'Яблоня «Симиренко»',
        'slug': 'yablonya-simirenenko',
        'category': 'yabloni',
        'price': 1300,
        'is_featured': False,
        'description': 'Зимний сорт украинской селекции с крупными зелёными плодами.',
        'care_tips': 'Морозостойкий сорт, подходит для средней полосы России.',
        'specs': [
            ('Сорт', 'Зимний', 'snowflake'),
            ('Высота', '3–5 м', 'ruler'),
        ],
    },
    {
        'name': 'Груша «Лада»',
        'slug': 'grusha-lada',
        'category': 'grushi',
        'price': 1100,
        'tags': 'hit',
        'is_featured': True,
        'rating': 4.7,
        'rating_count': 9,
        'description': 'Раннелетний сорт с сочными плодами. Устойчив к болезням, высокоурожаен.',
        'care_tips': 'Посадка весной или осенью. Требует опылителя — «Чижовская» или «Отрадненская».',
        'specs': [
            ('Сорт', 'Летний', 'sun'),
            ('Высота', '3–4 м', 'ruler'),
            ('Морозостойкость', 'до −30°C', 'thermometer'),
        ],
    },
    {
        'name': 'Груша «Чижовская»',
        'slug': 'grusha-chizhevskaya',
        'category': 'grushi',
        'price': 1150,
        'is_featured': True,
        'description': 'Популярный летний сорт с нежными сладкими плодами.',
        'care_tips': 'Высокая зимостойкость. Хорошо растёт на суглинках.',
        'specs': [
            ('Сорт', 'Летний', 'sun'),
            ('Высота', '3–4 м', 'ruler'),
        ],
    },
    {
        'name': 'Слива «Венгерка»',
        'slug': 'sliva-vengerka',
        'category': 'slivy',
        'price': 1000,
        'old_price': 1250,
        'tags': 'sale',
        'is_featured': True,
        'description': 'Классический сорт сливы с синими плодами. Идеальна для варенья и джема.',
        'care_tips': 'Самоплодный сорт, не требует опылителя. Предпочитает супесчаные почвы.',
        'specs': [
            ('Тип', 'Самоплодная', 'check'),
            ('Высота', '2.5–3 м', 'ruler'),
            ('Урожай', 'Август–сентябрь', 'calendar'),
        ],
    },
    {
        'name': 'Слива «Анна Шпет»',
        'slug': 'sliva-anna-shpet',
        'category': 'slivy',
        'price': 1100,
        'is_featured': False,
        'description': 'Позднеспелый сорт с крупными тёмно-фиолетовыми плодами.',
        'care_tips': 'Нуждается в опылителях. Высокая урожайность при правильном уходе.',
        'specs': [],
    },
    {
        'name': 'Вишня «Шоколадница»',
        'slug': 'vishnya-shokoladnitsa',
        'category': 'vishni',
        'price': 1300,
        'tags': 'new',
        'is_featured': True,
        'rating': 4.9,
        'rating_count': 5,
        'description': 'Компактный сорт с тёмно-бордовыми плодами насыщенного вкуса.',
        'care_tips': 'Самоплодный, компактный. Подходит для небольших участков.',
        'specs': [
            ('Тип', 'Самоплодная', 'check'),
            ('Высота', '2–2.5 м', 'ruler'),
        ],
    },
    {
        'name': 'Черешня «Ипуть»',
        'slug': 'chereshnya-iput',
        'category': 'vishni',
        'price': 1800,
        'old_price': 2000,
        'tags': 'sale',
        'is_featured': True,
        'description': 'Раннеспелый сорт черешни с крупными тёмно-красными плодами.',
        'care_tips': 'Требует опылителей. Высаживайте несколько сортов рядом.',
        'specs': [
            ('Высота', '3–4 м', 'ruler'),
            ('Урожай', 'Июнь', 'calendar'),
        ],
    },
]

for pd in products_data:
    specs = pd.pop('specs', [])
    cat_slug = pd.pop('category')
    pd['category'] = categories[cat_slug]

    product, created = Product.objects.get_or_create(slug=pd['slug'], defaults=pd)
    if created:
        print(f'  Товар: {product.name}')
        for label, value, icon in specs:
            ProductSpecification.objects.create(
                product=product, label=label, value=value, icon=icon
            )
    else:
        print(f'  Товар уже существует: {product.name}')

print('\nДемо-данные загружены!')
print('   Запустите сервер: python manage.py runserver')
print('   Сайт: http://localhost:8000')
print('   Админка: http://localhost:8000/admin/')
