"""
python manage.py compress_static

Минифицирует CSS (и опционально JS) файлы в STATIC_ROOT после collectstatic.
Не требует внешних зависимостей — использует только stdlib re.

Что делает:
- Удаляет /* ... */ комментарии
- Схлопывает множественные пробелы/переводы строк
- Убирает пробелы вокруг: { } ; : , > + ~ =
- Убирает trailing ; перед }
"""
import os
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


def minify_css(src: str) -> str:
    # 1. Удалить комментарии
    out = re.sub(r'/\*.*?\*/', '', src, flags=re.DOTALL)
    # 2. Схлопнуть переводы строк и пробелы
    out = re.sub(r'\s+', ' ', out)
    # 3. Убрать пробелы вокруг спецсимволов
    out = re.sub(r'\s*([{};:,>+~=])\s*', r'\1', out)
    # 4. Убрать ; перед }
    out = out.replace(';}', '}')
    # 5. Убрать пробел после ( и перед )
    out = re.sub(r'\(\s+', '(', out)
    out = re.sub(r'\s+\)', ')', out)
    return out.strip()


class Command(BaseCommand):
    help = 'Minify CSS files in STATIC_ROOT in-place'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show savings without writing')

    def handle(self, *args, **options):
        static_root = Path(settings.STATIC_ROOT)
        if not static_root.exists():
            self.stderr.write('STATIC_ROOT does not exist. Run collectstatic first.')
            return

        dry_run = options['dry_run']
        total_saved = 0

        for css_file in static_root.rglob('*.css'):
            original = css_file.read_text(encoding='utf-8', errors='replace')
            minified = minify_css(original)

            original_size = len(original.encode('utf-8'))
            minified_size = len(minified.encode('utf-8'))
            saved         = original_size - minified_size
            total_saved  += saved

            pct = round(saved / original_size * 100) if original_size else 0
            self.stdout.write(
                f'  {css_file.relative_to(static_root)}: '
                f'{original_size//1024}KB -> {minified_size//1024}KB  (-{pct}%)'
            )

            if not dry_run and saved > 0:
                css_file.write_text(minified, encoding='utf-8')

        verb = 'Would save' if dry_run else 'Saved'
        self.stdout.write(self.style.SUCCESS(
            f'\n{verb} {total_saved // 1024} KB total across CSS files'
        ))
