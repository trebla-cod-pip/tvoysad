"""
Минимальные тесты middleware ActivityLogMiddleware.

Запуск:
    python manage.py test activity.tests.test_middleware
"""
import time
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase, RequestFactory
from django.http import HttpResponse

from activity.middleware import (
    ActivityLogMiddleware,
    _build_uid,
    _classify_event,
    _get_ip,
    SKIP_PREFIXES,
)
from activity.models import ActivityLog


# ─────────────────────────────────────────────
# Вспомогательные утилиты
# ─────────────────────────────────────────────

def _make_response(status=200):
    return HttpResponse(status=status)


def _dummy_get_response(request):
    return _make_response()


# ─────────────────────────────────────────────
# Тесты вспомогательных функций
# ─────────────────────────────────────────────

class UtilsTests(TestCase):

    def test_get_ip_remote_addr(self):
        factory = RequestFactory()
        req = factory.get('/', REMOTE_ADDR='1.2.3.4')
        self.assertEqual(_get_ip(req), '1.2.3.4')

    def test_get_ip_forwarded(self):
        factory = RequestFactory()
        req = factory.get('/', HTTP_X_FORWARDED_FOR='5.6.7.8, 1.2.3.4')
        self.assertEqual(_get_ip(req), '5.6.7.8')

    def test_build_uid_uses_session_key(self):
        uid1 = _build_uid('abc123', '1.1.1.1', 'Mozilla')
        uid2 = _build_uid('abc123', '9.9.9.9', 'Chrome')
        # одинаковый session_key → одинаковый uid
        self.assertEqual(uid1, uid2)

    def test_build_uid_different_sessions(self):
        uid1 = _build_uid('session-A', '1.1.1.1', 'Mozilla')
        uid2 = _build_uid('session-B', '1.1.1.1', 'Mozilla')
        self.assertNotEqual(uid1, uid2)

    def test_build_uid_fallback_ip_ua(self):
        uid = _build_uid('', '1.2.3.4', 'TestAgent')
        self.assertEqual(len(uid), 16)

    def test_build_uid_length(self):
        uid = _build_uid('my-session', '', '')
        self.assertEqual(len(uid), 16)

    def test_classify_event_api(self):
        factory = RequestFactory()
        req = factory.get('/api/products/')
        self.assertEqual(_classify_event(req, 200), 'api')

    def test_classify_event_auth_login(self):
        factory = RequestFactory()
        req = factory.post('/login/')
        self.assertEqual(_classify_event(req, 302), 'auth')

    def test_classify_event_auth_logout(self):
        factory = RequestFactory()
        req = factory.get('/logout/')
        self.assertEqual(_classify_event(req, 302), 'auth')

    def test_classify_event_form_post(self):
        factory = RequestFactory()
        req = factory.post('/checkout/')
        self.assertEqual(_classify_event(req, 200), 'form')

    def test_classify_event_error(self):
        factory = RequestFactory()
        req = factory.get('/some-page/')
        self.assertEqual(_classify_event(req, 500), 'error')

    def test_classify_event_pageview(self):
        factory = RequestFactory()
        req = factory.get('/catalog/')
        self.assertEqual(_classify_event(req, 200), 'pageview')


# ─────────────────────────────────────────────
# Тесты middleware
# ─────────────────────────────────────────────

class MiddlewareTests(TransactionTestCase):
    # TransactionTestCase нужен, потому что _write_log работает в отдельном потоке:
    # стандартный TestCase оборачивает тесты в транзакцию, невидимую другому соединению.

    def setUp(self):
        self.factory = RequestFactory()
        self.mw = ActivityLogMiddleware(_dummy_get_response)

    def _process(self, request, status=200):
        """Прогнать запрос через middleware и дождаться записи в БД."""
        self.mw.process_request(request)
        response = _make_response(status)
        self.mw.process_response(request, response)
        # _write_log работает в потоке; даём ему завершиться
        time.sleep(0.05)
        return response

    def test_pageview_is_logged(self):
        req = self.factory.get('/catalog/', REMOTE_ADDR='10.0.0.1')
        req.session = type('S', (), {'session_key': 'test-key-1'})()
        self._process(req)
        self.assertEqual(ActivityLog.objects.filter(path='/catalog/').count(), 1)

    def test_static_not_logged(self):
        req = self.factory.get('/static/css/main.css', REMOTE_ADDR='10.0.0.1')
        req.session = type('S', (), {'session_key': 'test-key-2'})()
        self._process(req)
        self.assertEqual(ActivityLog.objects.filter(path__startswith='/static/').count(), 0)

    def test_media_not_logged(self):
        req = self.factory.get('/media/img.jpg', REMOTE_ADDR='10.0.0.1')
        req.session = type('S', (), {'session_key': 'test-key-3'})()
        self._process(req)
        self.assertEqual(ActivityLog.objects.filter(path__startswith='/media/').count(), 0)

    def test_favicon_not_logged(self):
        req = self.factory.get('/favicon.ico', REMOTE_ADDR='10.0.0.1')
        req.session = type('S', (), {'session_key': 'test-key-4'})()
        self._process(req)
        self.assertEqual(ActivityLog.objects.filter(path='/favicon.ico').count(), 0)

    def test_status_code_stored(self):
        req = self.factory.get('/some-page/', REMOTE_ADDR='10.0.0.1')
        req.session = type('S', (), {'session_key': 'test-key-5'})()
        self._process(req, status=404)
        log = ActivityLog.objects.get(path='/some-page/')
        self.assertEqual(log.status_code, 404)

    def test_uid_consistent_for_same_session(self):
        for i in range(2):
            req = self.factory.get('/page/', REMOTE_ADDR='10.0.0.1')
            req.session = type('S', (), {'session_key': 'same-session'})()
            self._process(req)

        logs = list(ActivityLog.objects.filter(path='/page/').values_list('uid', flat=True))
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0], logs[1])

    def test_response_time_recorded(self):
        req = self.factory.get('/catalog/', REMOTE_ADDR='10.0.0.1')
        req.session = type('S', (), {'session_key': 'test-key-6'})()
        self._process(req)
        log = ActivityLog.objects.get(path='/catalog/')
        self.assertGreaterEqual(log.response_time_ms, 0)

    def test_exception_in_logger_does_not_raise(self):
        """Если запись в БД упала — ответ всё равно возвращается."""
        req = self.factory.get('/catalog/', REMOTE_ADDR='10.0.0.1')
        req.session = type('S', (), {'session_key': 'test-key-7'})()
        with patch('activity.middleware._write_log', side_effect=RuntimeError('boom')):
            # middleware сам ловит ошибки из потока — ответ должен вернуться
            response = self.mw.process_response(req, _make_response())
        self.assertEqual(response.status_code, 200)
