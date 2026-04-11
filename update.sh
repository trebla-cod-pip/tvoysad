#!/usr/bin/env bash
# =============================================================================
# update.sh — обновление сайта с GitHub без даунтайма
# Запускать из корня проекта: bash update.sh
# =============================================================================
set -euo pipefail

PYTHON_BIN="$(pwd)/venv/bin/python"

echo "[INFO] Получаем изменения из GitHub..."
git pull origin main

echo "[INFO] Устанавливаем новые зависимости (если появились)..."
venv/bin/pip install -r requirements.txt --quiet

echo "[INFO] Применяем миграции..."
"$PYTHON_BIN" manage.py migrate --noinput

echo "[INFO] Собираем статику..."
"$PYTHON_BIN" manage.py collectstatic --noinput --clear

echo "[INFO] Минифицируем CSS..."
"$PYTHON_BIN" manage.py compress_static

echo "[INFO] Генерируем WebP-миниатюры..."
"$PYTHON_BIN" manage.py generate_webp

echo "[INFO] Перезапускаем Gunicorn..."
systemctl restart tvoysad

echo "[OK] Сайт обновлён!"
