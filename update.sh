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

echo "[INFO] Обновляем конфиг Nginx..."
NGINX_CONF="/etc/nginx/sites-available/tvoysad"
CERT_PATH="/etc/letsencrypt/live/tlpn.shop/fullchain.pem"

if [ -f "$CERT_PATH" ]; then
    sudo cp nginx.conf "$NGINX_CONF"
    echo "[INFO] Конфиг скопирован (с HTTPS)"
else
    # Сертификат ещё не получен — используем HTTP-only версию
    echo "[WARN] Сертификат Let's Encrypt не найден, применяем HTTP-only конфиг"
    sudo tee "$NGINX_CONF" > /dev/null <<'NGINX_HTTP'
server {
    listen 80;
    server_name tlpn.shop www.tlpn.shop;

    client_max_body_size 20M;

    location /static/ {
        alias /opt/tvoysad/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        add_header Vary "Accept-Encoding";
        access_log off;
    }

    location /media/ {
        alias /opt/tvoysad/media/;
        expires 30d;
        add_header Cache-Control "public";
        access_log off;
    }

    location = /favicon.ico {
        alias /opt/tvoysad/staticfiles/favicon.ico;
        expires 7d;
        access_log off;
        log_not_found off;
    }

    location / {
        proxy_pass         http://unix:/run/tvoysad.sock;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
        proxy_connect_timeout 5s;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}
NGINX_HTTP
fi

if sudo nginx -t 2>/dev/null; then
    sudo systemctl reload nginx
    echo "[OK] Nginx перезагружен"
else
    echo "[ERROR] Конфиг Nginx невалиден, откат..."
    sudo nginx -t
    exit 1
fi

echo "[INFO] Перезапускаем Gunicorn..."
sudo systemctl restart tvoysad

echo "[OK] Сайт обновлён!"
