import json
import urllib.request

from django.conf import settings
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import get_object_or_404, render

from .models import TelegramUser, TelegramVisit


class TelegramVisitInline(admin.TabularInline):
    model = TelegramVisit
    extra = 0
    readonly_fields = ('created_at', 'page', 'platform', 'screen_width', 'screen_height', 'theme', 'user_agent')
    can_delete = False
    max_num = 0
    ordering = ['-created_at']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = (
        'tg_id', 'full_name_display', 'username_link', 'platform',
        'language_code', 'is_premium', 'allows_write_to_pm',
        'visits_count', 'last_seen', 'send_msg_btn',
    )
    list_filter = ('platform', 'language_code', 'is_premium', 'allows_write_to_pm')
    search_fields = ('tg_id', 'username', 'first_name', 'last_name')
    readonly_fields = (
        'tg_id', 'username', 'first_name', 'last_name', 'language_code',
        'is_premium', 'allows_write_to_pm', 'photo_url', 'photo_preview',
        'platform', 'tg_version', 'client_platform',
        'visits_count', 'created_at', 'last_seen',
    )
    inlines = [TelegramVisitInline]
    ordering = ['-last_seen']

    fieldsets = (
        ('Пользователь', {
            'fields': ('tg_id', 'first_name', 'last_name', 'username', 'photo_preview', 'photo_url')
        }),
        ('Параметры', {
            'fields': ('language_code', 'is_premium', 'allows_write_to_pm')
        }),
        ('Устройство', {
            'fields': ('platform', 'tg_version', 'client_platform')
        }),
        ('Статистика', {
            'fields': ('visits_count', 'created_at', 'last_seen')
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:pk>/send/', self.admin_site.admin_view(self.send_message_view), name='tg_user_send'),
        ]
        return custom + urls

    def full_name_display(self, obj):
        return obj.full_name or '—'
    full_name_display.short_description = 'Имя'

    def username_link(self, obj):
        if obj.tg_link:
            return format_html('<a href="{}" target="_blank">@{}</a>', obj.tg_link, obj.username)
        return '—'
    username_link.short_description = 'Username'

    def photo_preview(self, obj):
        if obj.photo_url:
            return format_html('<img src="{}" style="width:64px;height:64px;border-radius:50%">', obj.photo_url)
        return '—'
    photo_preview.short_description = 'Фото'

    def send_msg_btn(self, obj):
        if obj.allows_write_to_pm:
            url = reverse('admin:tg_user_send', args=[obj.pk])
            return format_html('<a class="button" href="{}">✉ Написать</a>', url)
        return format_html('<span style="color:#999">ЛС закрыты</span>')
    send_msg_btn.short_description = 'Сообщение'

    def send_message_view(self, request, pk):
        user = get_object_or_404(TelegramUser, pk=pk)
        if request.method == 'POST':
            text = request.POST.get('text', '').strip()
            if text:
                bot_token = getattr(settings, 'TG_BOT_TOKEN', '')
                if not bot_token:
                    self.message_user(request, 'TG_BOT_TOKEN не настроен в .env', messages.ERROR)
                else:
                    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
                    payload = json.dumps({
                        'chat_id': user.tg_id,
                        'text': text,
                        'parse_mode': 'HTML',
                    }).encode()
                    req = urllib.request.Request(
                        url, data=payload,
                        headers={'Content-Type': 'application/json'}
                    )
                    try:
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            result = json.loads(resp.read())
                        if result.get('ok'):
                            self.message_user(request, f'Сообщение отправлено пользователю {user}')
                        else:
                            self.message_user(request, f'Ошибка Telegram: {result}', messages.ERROR)
                    except Exception as e:
                        self.message_user(request, f'Ошибка: {e}', messages.ERROR)
            return HttpResponseRedirect(reverse('admin:tg_users_telegramuser_change', args=[pk]))

        context = {
            **self.admin_site.each_context(request),
            'tg_user': user,
            'opts': self.model._meta,
            'title': f'Написать {user}',
        }
        return render(request, 'admin/tg_users/send_message.html', context)

    def has_add_permission(self, request):
        return False


@admin.register(TelegramVisit)
class TelegramVisitAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'page', 'platform', 'screen_width', 'screen_height', 'theme')
    list_filter = ('platform', 'theme', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'page')
    readonly_fields = ('user', 'page', 'platform', 'screen_width', 'screen_height', 'user_agent', 'theme', 'created_at')
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False
