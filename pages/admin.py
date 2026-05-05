import json
import urllib.error
import urllib.request

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from .models import Page, ContactMessage, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Контакты', {
            'fields': ('phone', 'phone_delivery', 'email', 'schedule', 'address'),
        }),
        ('Доставка', {
            'fields': ('courier_price',),
        }),
        ('Изображения', {
            'fields': ('hero_image',),
        }),
        ('Telegram-уведомления', {
            'fields': ('tg_bot_token', 'tg_admin_chat_id', 'tg_test_button'),
            'description': (
                'Укажите токен бота и Chat ID администратора, '
                'чтобы получать уведомления о новых заказах в Telegram.'
            ),
        }),
    )
    readonly_fields = ('tg_test_button',)

    def tg_test_button(self, obj):
        url = reverse('admin:pages_sitesettings_test_tg')
        return format_html(
            '<a class="button" href="{}" style="'
            'display:inline-block;padding:8px 16px;background:#417690;'
            'color:#fff;border-radius:4px;text-decoration:none;font-size:13px">'
            'Отправить тестовое сообщение</a>',
            url,
        )
    tg_test_button.short_description = 'Проверка связи'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('test-tg/', self.admin_site.admin_view(self._test_tg_view),
                 name='pages_sitesettings_test_tg'),
        ]
        return custom + urls

    def _test_tg_view(self, request):
        s = SiteSettings.get()
        token = s.tg_bot_token.strip()
        chat_id = s.tg_admin_chat_id.strip()
        changelist_url = reverse('admin:pages_sitesettings_changelist')

        if not token:
            self.message_user(request, 'Поле «Telegram Bot Token» не заполнено.', level=messages.ERROR)
            return HttpResponseRedirect(changelist_url)
        if not chat_id:
            self.message_user(request, 'Поле «Telegram Chat ID администратора» не заполнено.', level=messages.ERROR)
            return HttpResponseRedirect(changelist_url)

        # Проверяем токен
        try:
            resp = urllib.request.urlopen(
                f'https://api.telegram.org/bot{token}/getMe', timeout=10
            )
            bot = json.loads(resp.read()).get('result', {})
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            self.message_user(request, f'Неверный токен бота: {body}', level=messages.ERROR)
            return HttpResponseRedirect(changelist_url)
        except Exception as e:
            self.message_user(request, f'Ошибка подключения к Telegram: {e}', level=messages.ERROR)
            return HttpResponseRedirect(changelist_url)

        # Отправляем тест
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
                self.message_user(
                    request,
                    f'Тестовое сообщение отправлено боту @{bot.get("username")} в чат {chat_id}.',
                    level=messages.SUCCESS,
                )
            else:
                self.message_user(request, f'Telegram ответил ошибкой: {data}', level=messages.ERROR)
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            self.message_user(request, f'Ошибка sendMessage: {body}', level=messages.ERROR)
        except Exception as e:
            self.message_user(request, f'Ошибка: {e}', level=messages.ERROR)

        return HttpResponseRedirect(changelist_url)

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_published')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact', 'is_read', 'created_at')
    list_editable = ('is_read',)
    list_filter = ('is_read',)
    readonly_fields = ('created_at',)
