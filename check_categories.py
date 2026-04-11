#!/usr/bin/env python
"""
Скрипт для проверки существующих категорий и загрузки фикстуры деревьев
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from catalog.models import Category

print("Существующие категории:")
for cat in Category.objects.all():
    print(f"  ID={cat.id}, Name={cat.name}, Slug={cat.slug}")
