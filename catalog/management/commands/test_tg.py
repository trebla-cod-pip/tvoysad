import json
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand

from pages.models import SiteSettings


class Command(BaseCommand):
    help = 'Проверяет Telegram-уведомления: читает настройки и отправляет тестовое сообщение'

    def handle(self, *args, **options):
        s = SiteSettings.get()
        token = s.tg_bot_token.strip()
        chat_id = s.tg_admin_chat_id.strip()

        self.stdout.write(f'tg_bot_token:      {"[OK] задан" if token else "[!] ПУСТО"}')
        self.stdout.write(f'tg_admin_chat_id:  {"[OK] " + chat_id if chat_id else "[!] ПУСТО"}')

        if not token or not chat_id:
            self.stderr.write(
                '\nЗаполните поля в Админке → Настройки сайта → Telegram-уведомления'
            )
            return

        # Проверяем токен через getMe
        self.stdout.write('\n→ Проверяю токен (getMe)...')
        try:
            resp = urllib.request.urlopen(
                f'https://api.telegram.org/bot{token}/getMe', timeout=10
            )
            data = json.loads(resp.read())
            bot = data.get('result', {})
            self.stdout.write(
                self.style.SUCCESS(
                    f'  Bot: @{bot.get("username")} ({bot.get("first_name")})'
                )
            )
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            self.stderr.write(f'  Ошибка getMe {e.code}: {body}')
            return
        except Exception as e:
            self.stderr.write(f'  Ошибка getMe: {e}')
            return

        # Отправляем тестовое сообщение
        self.stdout.write(f'\n→ Отправляю тестовое сообщение в chat_id={chat_id}...')
        payload = json.dumps({
            'chat_id': chat_id,
            'text': '<b>Тест уведомлений</b>\n\nСвязь с ботом работает — уведомления о заказах будут приходить сюда.',
            'parse_mode': 'HTML',
        }).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=payload,
            headers={'Content-Type': 'application/json'},
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            if data.get('ok'):
                self.stdout.write(self.style.SUCCESS('  OK: сообщение отправлено!'))
            else:
                self.stderr.write(f'  Telegram вернул ошибку: {data}')
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            self.stderr.write(f'  Ошибка sendMessage {e.code}: {body}')
        except Exception as e:
            self.stderr.write(f'  Ошибка sendMessage: {e}')
