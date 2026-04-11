import hashlib
import threading
import time
from datetime import datetime, timezone

from django.utils.deprecation import MiddlewareMixin

# Пути, которые не нужно логировать
SKIP_PREFIXES = ('/static/', '/media/', '/favicon.ico', '/health')
SKIP_EXACT    = {'/favicon.ico'}


def _get_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _build_uid(session_key, ip, user_agent):
    """
    UID = первые 16 символов SHA-256 от (session_key | ip+ua).
    Стабилен на протяжении сессии, разный у разных браузеров/IP.
    """
    if session_key:
        raw = session_key
    else:
        raw = f'{ip}:{user_agent}'
    return hashlib.sha256(raw.encode('utf-8', errors='replace')).hexdigest()[:16]


def _classify_event(request, status_code):
    path   = request.path
    method = request.method

    if path in ('/login/', '/logout/') or path.startswith('/admin/login') or path.startswith('/admin/logout'):
        return 'auth'
    if path.startswith('/api/'):
        return 'api'
    if status_code >= 500:
        return 'error'
    if method == 'POST':
        return 'form'
    return 'pageview'


def _write_log(data: dict):
    """Выполняется в отдельном потоке — сбой не влияет на ответ."""
    try:
        from activity.models import ActivityLog
        ActivityLog.objects.create(**data)
    except Exception:
        pass  # сбой логирования не должен ронять сайт


class ActivityLogMiddleware(MiddlewareMixin):
    """
    Логирует каждый HTTP-запрос в ActivityLog асинхронно (отдельный поток).
    """

    def process_request(self, request):
        request._activity_start = time.monotonic()

    def process_response(self, request, response):
        try:
            path = request.path

            # Пропускаем статику, медиа, healthcheck
            if any(path.startswith(p) for p in SKIP_PREFIXES) or path in SKIP_EXACT:
                return response

            start = getattr(request, '_activity_start', None)
            elapsed_ms = int((time.monotonic() - start) * 1000) if start is not None else 0

            ip          = _get_ip(request)
            user_agent  = request.META.get('HTTP_USER_AGENT', '')
            session_key = ''
            try:
                # session может не существовать (пустой запрос без куки)
                session_key = request.session.session_key or ''
            except Exception:
                pass

            uid        = _build_uid(session_key, ip, user_agent)
            status     = response.status_code
            event_type = _classify_event(request, status)

            user_id = None
            try:
                if request.user.is_authenticated:
                    user_id = request.user.pk
            except Exception:
                pass

            data = dict(
                uid              = uid,
                session_key      = session_key,
                ip_address       = ip or None,
                timestamp        = datetime.now(tz=timezone.utc),
                method           = request.method,
                path             = path,
                query_string     = request.META.get('QUERY_STRING', ''),
                status_code      = status,
                response_time_ms = elapsed_ms,
                referrer         = request.META.get('HTTP_REFERER', ''),
                user_agent       = user_agent,
                event_type       = event_type,
                user_id          = user_id,
            )

            t = threading.Thread(target=_write_log, args=(data,), daemon=True)
            t.start()

        except Exception:
            pass  # защита: никакой ошибки наружу

        return response
