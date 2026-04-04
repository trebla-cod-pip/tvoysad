#!/usr/bin/env bash
# =============================================================================
# deploy.sh — развёртывание проекта «Твой Сад» на Ubuntu 20.04 / 22.04 / 24.04
# Запускать из корня проекта (там же, где manage.py):
#   bash deploy.sh
# =============================================================================

set -euo pipefail

# ── Цветной вывод ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Проверяем, что запускаемся из корня проекта ───────────────────────────────
[[ -f "manage.py" ]] || error "manage.py не найден. Запустите скрипт из корня Django-проекта."

PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

echo -e "\n${BOLD}==============================${NC}"
echo -e "${BOLD}  Деплой: Твой Сад${NC}"
echo -e "${BOLD}==============================${NC}\n"

# =============================================================================
# 1. Системные зависимости
# =============================================================================
info "Шаг 1/7 — Проверка системных пакетов"

NEED_APT=()
for pkg in python3 python3-pip python3-venv; do
    if ! dpkg -s "$pkg" &>/dev/null; then
        NEED_APT+=("$pkg")
    fi
done

if [[ ${#NEED_APT[@]} -gt 0 ]]; then
    warn "Не установлены: ${NEED_APT[*]}. Устанавливаем..."
    sudo apt-get update -qq
    sudo apt-get install -y "${NEED_APT[@]}"
    success "Пакеты установлены: ${NEED_APT[*]}"
else
    success "Все системные пакеты уже установлены"
fi

# =============================================================================
# 2. Виртуальное окружение
# =============================================================================
info "Шаг 2/7 — Виртуальное окружение"

if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
    success "Создано venv в $VENV_DIR"
else
    success "venv уже существует"
fi

# «Активируем» для последующих команд через полный путь к бинарникам
# (set -e не позволяет использовать source в скрипте надёжно)

# =============================================================================
# 3. Зависимости Python
# =============================================================================
info "Шаг 3/7 — Установка зависимостей Python"

"$PIP_BIN" install --upgrade pip --quiet
if [[ -f "requirements.txt" ]]; then
    "$PIP_BIN" install -r requirements.txt --quiet
    success "Зависимости из requirements.txt установлены"
else
    warn "requirements.txt не найден, пропускаем"
fi

# =============================================================================
# 4. Файл .env
# =============================================================================
info "Шаг 4/7 — Проверка .env"

if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        warn "Создан .env из .env.example — ОБЯЗАТЕЛЬНО заполните SECRET_KEY и другие параметры!"
    else
        warn ".env не найден и .env.example отсутствует."
        warn "Создайте .env вручную. Минимальный пример:"
        echo -e "    SECRET_KEY=your-very-secret-key-here"
        echo -e "    DEBUG=False"
        echo -e "    ALLOWED_HOSTS=your-domain.com,www.your-domain.com"
        echo ""
        read -r -p "Продолжить без .env? [y/N] " CONTINUE_WITHOUT_ENV
        [[ "${CONTINUE_WITHOUT_ENV,,}" == "y" ]] || error "Прервано. Создайте .env и перезапустите скрипт."
    fi
else
    success ".env найден"
fi

# =============================================================================
# 5. Django: migrate, collectstatic, createsuperuser
# =============================================================================
info "Шаг 5/7 — Миграции базы данных"
"$PYTHON_BIN" manage.py migrate --noinput
success "Миграции применены"

info "Шаг 5b — Сбор статических файлов"
mkdir -p staticfiles
"$PYTHON_BIN" manage.py collectstatic --noinput --clear
success "Статика собрана в staticfiles/"

# Предлагаем создать суперпользователя только если в БД нет ни одного
SUPERUSER_EXISTS=$("$PYTHON_BIN" - <<'EOF'
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.contrib.auth import get_user_model
print(get_user_model().objects.filter(is_superuser=True).exists())
EOF
)
if [[ "$SUPERUSER_EXISTS" == "False" ]]; then
    echo ""
    warn "Суперпользователи не найдены."
    read -r -p "Создать суперпользователя сейчас? [Y/n] " CREATE_SU
    if [[ "${CREATE_SU,,}" != "n" ]]; then
        "$PYTHON_BIN" manage.py createsuperuser
    fi
else
    success "Суперпользователь уже существует"
fi

# =============================================================================
# 6. Gunicorn
# =============================================================================
info "Шаг 6/7 — Проверка / установка Gunicorn"

if ! "$VENV_DIR/bin/gunicorn" --version &>/dev/null 2>&1; then
    "$PIP_BIN" install gunicorn --quiet
    success "Gunicorn установлен"
else
    success "Gunicorn уже установлен ($("$VENV_DIR/bin/gunicorn" --version))"
fi

# Выясняем имя пакета с настройками Django (ищем первый каталог рядом с manage.py
# где лежит wsgi.py)
DJANGO_MODULE=$(find . -maxdepth 3 -name "wsgi.py" ! -path "*/venv/*" \
    | head -1 | sed 's|^\./||;s|/wsgi.py||;s|/|.|g')

if [[ -z "$DJANGO_MODULE" ]]; then
    warn "wsgi.py не найден автоматически. Укажите WSGI-модуль вручную ниже."
    WSGI_APP="config.wsgi:application"
else
    WSGI_APP="${DJANGO_MODULE}.wsgi:application"
fi

success "WSGI-приложение: $WSGI_APP"

# =============================================================================
# 7. Systemd-сервис для Gunicorn (опционально)
# =============================================================================
info "Шаг 7/7 — Создание systemd-сервиса"

SERVICE_NAME="tvoysad"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
CURRENT_USER="${SUDO_USER:-$USER}"
WORKERS=$(( $(nproc) * 2 + 1 ))
# Не более 9 воркеров на небольшом VPS
[[ $WORKERS -gt 9 ]] && WORKERS=9

read -r -p "Создать/обновить systemd-сервис ${SERVICE_NAME}.service? [Y/n] " CREATE_SERVICE
if [[ "${CREATE_SERVICE,,}" != "n" ]]; then
    sudo tee "$SERVICE_FILE" > /dev/null <<SERVICE
[Unit]
Description=Gunicorn — Твой Сад
After=network.target

[Service]
User=${CURRENT_USER}
Group=www-data
WorkingDirectory=${PROJECT_DIR}
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${VENV_DIR}/bin/gunicorn \\
    --workers ${WORKERS} \\
    --bind unix:/run/${SERVICE_NAME}.sock \\
    --access-logfile ${PROJECT_DIR}/logs/gunicorn-access.log \\
    --error-logfile  ${PROJECT_DIR}/logs/gunicorn-error.log \\
    ${WSGI_APP}
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure

[Install]
WantedBy=multi-user.target
SERVICE

    mkdir -p "$PROJECT_DIR/logs"
    sudo systemctl daemon-reload
    sudo systemctl enable  "$SERVICE_NAME"
    sudo systemctl restart "$SERVICE_NAME"

    sleep 1
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        success "Сервис $SERVICE_NAME запущен и включён в автозапуск"
    else
        warn "Сервис не запустился. Проверьте: sudo journalctl -u $SERVICE_NAME -n 50"
    fi
else
    info "Systemd-сервис пропущен."
    echo ""
    echo -e "  Для ручного запуска Gunicorn:"
    echo -e "    source venv/bin/activate"
    echo -e "    gunicorn --workers 3 --bind 0.0.0.0:8000 $WSGI_APP"
fi

# =============================================================================
# Nginx — подсказка
# =============================================================================
SOCK_PATH="/run/${SERVICE_NAME}.sock"
echo ""
echo -e "${BOLD}----------------------------------------------------------------------${NC}"
echo -e "${BOLD}  Пример конфига Nginx (сохраните в /etc/nginx/sites-available/tvoysad)${NC}"
echo -e "${BOLD}----------------------------------------------------------------------${NC}"
cat <<NGINX
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    client_max_body_size 20M;

    location /static/ {
        alias ${PROJECT_DIR}/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias ${PROJECT_DIR}/media/;
        expires 30d;
    }

    location / {
        proxy_pass http://unix:${SOCK_PATH};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

echo ""
echo -e "  Включить сайт и перезагрузить Nginx:"
echo -e "    sudo ln -s /etc/nginx/sites-available/tvoysad /etc/nginx/sites-enabled/"
echo -e "    sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo -e "  HTTPS (Let's Encrypt):"
echo -e "    sudo apt install certbot python3-certbot-nginx"
echo -e "    sudo certbot --nginx -d your-domain.com -d www.your-domain.com"
echo -e "${BOLD}----------------------------------------------------------------------${NC}"
echo ""
success "Деплой завершён!"
