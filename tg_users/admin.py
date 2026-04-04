import json
import urllib.request

from django.conf import settings
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import get_object_or_404, render

from .models import TelegramUser, TelegramVisit, TelegramMessage
from .views import send_message_to_user


# ── Inlines ───────────────────────────────────────────────────────────────────

class TelegramVisitInline(admin.TabularInline):
    model = TelegramVisit
    extra = 0
    readonly_fields = ('created_at', 'page', 'platform', 'screen_width', 'screen_height', 'theme')
    can_delete = False
    max_num = 0
    ordering = ['-created_at']
    verbose_name_plural = 'История визитов'

    def has_add_permission(self, request, obj=None):
        return False


class TelegramMessageInline(admin.TabularInline):
    model = TelegramMessage
    extra = 0
    readonly_fields = ('sent_at', 'status_badge', 'text_short', 'read_at', 'error_text')
    fields = ('sent_at', 'status_badge', 'text_short', 'read_at', 'error_text')
    can_delete = False
    max_num = 0
    ordering = ['-sent_at']
    verbose_name_plural = 'История сообщений'

    def has_add_permission(self, request, obj=None):
        return False

    def text_short(self, obj):
        return obj.text[:80] + '…' if len(obj.text) > 80 else obj.text
    text_short.short_description = 'Текст'

    def status_badge(self, obj):
        colors = {'sent': '#2196F3', 'error': '#f44336', 'read': '#4CAF50'}
        color = colors.get(obj.status, '#999')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:12px;font-size:12px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Статус'


# ── TelegramUser ──────────────────────────────────────────────────────────────

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = (
        'tg_id', 'full_name_display', 'username_link', 'platform',
        'language_code', 'is_premium', 'visits_count',
        'messages_count', 'last_seen', 'send_msg_btn',
    )
    list_filter = ('platform', 'language_code', 'is_premium', 'allows_write_to_pm')
    search_fields = ('tg_id', 'username', 'first_name', 'last_name')
    readonly_fields = (
        'tg_id', 'username', 'first_name', 'last_name', 'language_code',
        'is_premium', 'allows_write_to_pm', 'photo_url', 'photo_preview',
        'platform', 'tg_version', 'client_platform',
        'visits_count', 'created_at', 'last_seen',
    )
    inlines = [TelegramMessageInline, TelegramVisitInline]
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
            path('setup-webhook/', self.admin_site.admin_view(self.setup_webhook_view), name='tg_setup_webhook'),
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

    def messages_count(self, obj):
        total = obj.messages.count()
        unread = obj.messages.filter(status='sent').count()
        if unread:
            return format_html('{} <span style="color:#2196F3;font-size:11px">({} не прочит.)</span>', total, unread)
        return total
    messages_count.short_description = 'Сообщений'

    def send_msg_btn(self, obj):
        url = reverse('admin:tg_user_send', args=[obj.pk])
        return format_html('<a class="button" href="{}">✉ Написать</a>', url)
    send_msg_btn.short_description = ''

    def send_message_view(self, request, pk):
        user = get_object_or_404(TelegramUser, pk=pk)
        if request.method == 'POST':
            text = request.POST.get('text', '').strip()
            if text:
                msg = send_message_to_user(user, text)
                if msg.status == TelegramMessage.STATUS_SENT:
                    self.message_user(request, f'✅ Сообщение отправлено пользователю {user}')
                else:
                    self.message_user(request, f'❌ Ошибка: {msg.error_text}', messages.ERROR)
            return HttpResponseRedirect(reverse('admin:tg_users_telegramuser_change', args=[pk]))

        history = user.messages.all()[:20]
        context = {
            **self.admin_site.each_context(request),
            'tg_user': user,
            'history': history,
            'opts': self.model._meta,
            'title': f'Написать {user}',
        }
        return render(request, 'admin/tg_users/send_message.html', context)

    def setup_webhook_view(self, request):
        """Регистрирует вебхук в Telegram."""
        bot_token = getattr(settings, 'TG_BOT_TOKEN', '')
        if not bot_token:
            self.message_user(request, 'TG_BOT_TOKEN не настроен в .env', messages.ERROR)
            return HttpResponseRedirect(reverse('admin:tg_users_telegramuser_changelist'))

        token_suffix = bot_token.split(':')[-1]
        domain = request.get_host()
        webhook_url = f'https://{domain}/api/tg/webhook/{token_suffix}/'
        try:
            url = f'https://api.telegram.org/bot{bot_token}/setWebhook'
            payload = json.dumps({'url': webhook_url, 'allowed_updates': ['message', 'callback_query']}).encode()
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
            if result.get('ok'):
                self.message_user(request, f'✅ Вебхук зарегистрирован: {webhook_url}')
            else:
                self.message_user(request, f'❌ Ошибка: {result.get("description")}', messages.ERROR)
        except Exception as e:
            self.message_user(request, f'❌ {e}', messages.ERROR)
        return HttpResponseRedirect(reverse('admin:tg_users_telegramuser_changelist'))

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['webhook_url'] = reverse('admin:tg_setup_webhook')
        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request):
        return False


# ── TelegramMessage ───────────────────────────────────────────────────────────

@admin.register(TelegramMessage)
class TelegramMessageAdmin(admin.ModelAdmin):
    list_display  = ('sent_at', 'user_link', 'text_short', 'status_badge', 'read_at')
    list_filter   = ('status', 'sent_at')
    search_fields = ('user__username', 'user__first_name', 'text')
    readonly_fields = ('user', 'text', 'status', 'tg_message_id', 'error_text', 'sent_at', 'read_at')
    ordering = ['-sent_at']

    def user_link(self, obj):
        url = reverse('admin:tg_users_telegramuser_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user)
    user_link.short_description = 'Пользователь'

    def text_short(self, obj):
        return obj.text[:60] + '…' if len(obj.text) > 60 else obj.text
    text_short.short_description = 'Текст'

    def status_badge(self, obj):
        cfg = {
            'sent':  ('#2196F3', '📤 Отправлено'),
            'error': ('#f44336', '❌ Ошибка'),
            'read':  ('#4CAF50', '✅ Прочитано'),
        }
        color, label = cfg.get(obj.status, ('#999', obj.status))
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 12px;border-radius:12px;font-size:12px">{}</span>',
            color, label
        )
    status_badge.short_description = 'Статус'

    def has_add_permission(self, request):
        return False


# ── TelegramVisit ─────────────────────────────────────────────────────────────

@admin.register(TelegramVisit)
class TelegramVisitAdmin(admin.ModelAdmin):
    list_display  = ('created_at', 'user', 'page', 'platform', 'screen_width', 'screen_height', 'theme')
    list_filter   = ('platform', 'theme', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'page')
    readonly_fields = ('user', 'page', 'platform', 'screen_width', 'screen_height', 'user_agent', 'theme', 'created_at')
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False
