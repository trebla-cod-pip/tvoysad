import hashlib
import hmac
import json
import os
from urllib.parse import parse_qsl

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import TelegramUser, TelegramVisit


def _validate_init_data(init_data: str) -> dict | None:
    """Проверяет подпись Telegram WebApp initData. Возвращает данные или None."""
    bot_token = getattr(settings, 'TG_BOT_TOKEN', '')
    if not bot_token:
        # Токен не настроен — пропускаем валидацию в dev-режиме
        try:
            params = dict(parse_qsl(init_data, strict_parsing=False))
            user_raw = params.get('user', '{}')
            return json.loads(user_raw)
        except Exception:
            return None

    try:
        params = dict(parse_qsl(init_data, strict_parsing=False))
        received_hash = params.pop('hash', '')
        data_check_string = '\n'.join(
            f'{k}={v}' for k, v in sorted(params.items())
        )
        secret_key = hmac.new(
            b'WebAppData', bot_token.encode(), hashlib.sha256
        ).digest()
        expected_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            return None
        user_raw = params.get('user', '{}')
        return json.loads(user_raw)
    except Exception:
        return None


@csrf_exempt
@require_POST
def tg_init(request):
    """Принимает данные Telegram WebApp, сохраняет пользователя и визит."""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'invalid json'}, status=400)

    init_data = body.get('initData', '')
    tg_user_data = body.get('user')  # fallback если initData пустой (dev)

    if init_data:
        tg_user_data = _validate_init_data(init_data)

    if not tg_user_data or not tg_user_data.get('id'):
        return JsonResponse({'ok': False, 'error': 'no user'}, status=400)

    tg_id = tg_user_data['id']

    user, _ = TelegramUser.objects.get_or_create(tg_id=tg_id)
    user.first_name = tg_user_data.get('first_name', user.first_name)
    user.last_name = tg_user_data.get('last_name', user.last_name)
    user.username = tg_user_data.get('username', user.username)
    user.language_code = tg_user_data.get('language_code', user.language_code)
    user.is_premium = tg_user_data.get('is_premium', False)
    user.allows_write_to_pm = tg_user_data.get('allows_write_to_pm', False)
    user.photo_url = tg_user_data.get('photo_url', user.photo_url)
    user.platform = body.get('platform', user.platform)
    user.tg_version = body.get('version', user.tg_version)
    user.client_platform = body.get('clientPlatform', user.client_platform)
    user.visits_count += 1
    user.save()

    TelegramVisit.objects.create(
        user=user,
        page=body.get('page', '/'),
        platform=body.get('platform', ''),
        screen_width=body.get('screenWidth'),
        screen_height=body.get('screenHeight'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        theme=body.get('colorScheme', ''),
    )

    return JsonResponse({'ok': True, 'user_id': user.id})


@csrf_exempt
@require_POST
def tg_send_message(request):
    """Отправляет сообщение пользователю в Telegram."""
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'invalid json'}, status=400)

    tg_id = body.get('tg_id')
    text = body.get('text', '').strip()

    if not tg_id or not text:
        return JsonResponse({'ok': False, 'error': 'missing tg_id or text'}, status=400)

    bot_token = getattr(settings, 'TG_BOT_TOKEN', '')
    if not bot_token:
        return JsonResponse({'ok': False, 'error': 'TG_BOT_TOKEN not configured'}, status=500)

    import urllib.request
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = json.dumps({'chat_id': tg_id, 'text': text, 'parse_mode': 'HTML'}).encode()
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return JsonResponse({'ok': result.get('ok', False)})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
