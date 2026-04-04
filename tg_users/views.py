import hashlib
import hmac
import json
import urllib.request
from urllib.parse import parse_qsl

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import TelegramUser, TelegramVisit, TelegramMessage


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_init_data(init_data: str) -> dict | None:
    bot_token = getattr(settings, 'TG_BOT_TOKEN', '')
    if not bot_token:
        try:
            params = dict(parse_qsl(init_data, strict_parsing=False))
            return json.loads(params.get('user', '{}'))
        except Exception:
            return None
    try:
        params = dict(parse_qsl(init_data, strict_parsing=False))
        received_hash = params.pop('hash', '')
        data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(params.items()))
        secret_key = hmac.new(b'WebAppData', bot_token.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            return None
        return json.loads(params.get('user', '{}'))
    except Exception:
        return None


def _tg_api(method: str, payload: dict) -> dict:
    bot_token = getattr(settings, 'TG_BOT_TOKEN', '')
    url = f'https://api.telegram.org/bot{bot_token}/{method}'
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def send_message_to_user(user: TelegramUser, text: str) -> TelegramMessage:
    """Отправляет сообщение пользователю и сохраняет в истории."""
    msg = TelegramMessage(user=user, text=text)
    bot_token = getattr(settings, 'TG_BOT_TOKEN', '')
    if not bot_token:
        msg.status = TelegramMessage.STATUS_ERROR
        msg.error_text = 'TG_BOT_TOKEN не настроен'
        msg.save()
        return msg
    try:
        result = _tg_api('sendMessage', {
            'chat_id': user.tg_id,
            'text': text,
            'parse_mode': 'HTML',
        })
        if result.get('ok'):
            msg.status = TelegramMessage.STATUS_SENT
            msg.tg_message_id = result['result']['message_id']
        else:
            msg.status = TelegramMessage.STATUS_ERROR
            msg.error_text = result.get('description', 'Unknown error')[:500]
    except Exception as e:
        msg.status = TelegramMessage.STATUS_ERROR
        msg.error_text = str(e)[:500]
    msg.save()
    return msg


# ── API endpoints ─────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def tg_init(request):
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'invalid json'}, status=400)

    init_data = body.get('initData', '')
    tg_user_data = body.get('user')

    if init_data:
        tg_user_data = _validate_init_data(init_data)

    if not tg_user_data or not tg_user_data.get('id'):
        return JsonResponse({'ok': False, 'error': 'no user'}, status=400)

    tg_id = tg_user_data['id']
    user, _ = TelegramUser.objects.get_or_create(tg_id=tg_id)
    user.first_name        = tg_user_data.get('first_name', user.first_name)
    user.last_name         = tg_user_data.get('last_name', user.last_name)
    user.username          = tg_user_data.get('username', user.username)
    user.language_code     = tg_user_data.get('language_code', user.language_code)
    user.is_premium        = tg_user_data.get('is_premium', False)
    user.allows_write_to_pm = tg_user_data.get('allows_write_to_pm', False)
    user.photo_url         = tg_user_data.get('photo_url', user.photo_url)
    user.platform          = body.get('platform', user.platform)
    user.tg_version        = body.get('version', user.tg_version)
    user.client_platform   = body.get('clientPlatform', user.client_platform)
    user.visits_count     += 1
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
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'invalid json'}, status=400)

    tg_id = body.get('tg_id')
    text  = body.get('text', '').strip()
    if not tg_id or not text:
        return JsonResponse({'ok': False, 'error': 'missing tg_id or text'}, status=400)

    try:
        user = TelegramUser.objects.get(tg_id=tg_id)
    except TelegramUser.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'user not found'}, status=404)

    msg = send_message_to_user(user, text)
    return JsonResponse({'ok': msg.status == TelegramMessage.STATUS_SENT, 'status': msg.status})


@csrf_exempt
def tg_webhook(request, token):
    """Вебхук от Telegram — обновляет статус сообщений на «прочитано»."""
    bot_token = getattr(settings, 'TG_BOT_TOKEN', '')
    # Проверяем токен в URL для безопасности
    if not bot_token or token != bot_token.split(':')[-1]:
        return JsonResponse({'ok': False}, status=403)

    if request.method != 'POST':
        return JsonResponse({'ok': True})

    try:
        update = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': True})

    # Определяем tg_id отправителя
    tg_id = None
    message = update.get('message') or update.get('callback_query', {}).get('message')
    if message:
        sender = update.get('message', {}).get('from') or update.get('callback_query', {}).get('from')
        if sender:
            tg_id = sender.get('id')

    if tg_id:
        # Помечаем все неотвеченные сообщения этого пользователя как прочитанные
        now = timezone.now()
        updated = TelegramMessage.objects.filter(
            user__tg_id=tg_id,
            status=TelegramMessage.STATUS_SENT,
        ).update(status=TelegramMessage.STATUS_READ, read_at=now)

        # Обновляем last_seen пользователя
        TelegramUser.objects.filter(tg_id=tg_id).update(last_seen=now)

    return JsonResponse({'ok': True})
