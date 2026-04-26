import json
from datetime import timedelta

from django.contrib import admin
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import AdCampaign, AdClick

# ── Вспомогательные функции ────────────────────────────────────────────────

_SOURCE_ICON = {
    'vk': '🔵', 'instagram': '📸', 'telegram': '✈️',
    'facebook': '📘', 'yandex': '🔴', 'google': '🟢',
    'flyer': '📄', 'other': '🔗',
}


def _sparkline_svg(daily_counts, days=30, width=120, height=32):
    """Мини-график SVG из словаря {date: count}."""
    today = timezone.localdate()
    values = [daily_counts.get(today - timedelta(days=i), 0) for i in range(days - 1, -1, -1)]
    max_v = max(values) or 1
    step = width / max(len(values) - 1, 1)
    pts = ' '.join(
        f'{i * step:.1f},{height - (v / max_v) * (height - 4) - 2:.1f}'
        for i, v in enumerate(values)
    )
    return mark_safe(
        f'<svg width="{width}" height="{height}" style="vertical-align:middle">'
        f'<polyline points="{pts}" fill="none" stroke="var(--primary,#4a7c59)" stroke-width="2"/>'
        f'</svg>'
    )


def _build_dashboard_context(request):
    now = timezone.now()
    periods = {'7': 7, '30': 30, '90': 90}
    days = int(request.GET.get('days', 30))

    cutoff = now - timedelta(days=days)
    campaigns = AdCampaign.objects.prefetch_related('clicks').order_by('-created_at')

    # Суммарные KPI
    total_clicks_period = AdClick.objects.filter(timestamp__gte=cutoff).count()
    total_clicks_all    = AdClick.objects.count()
    active_campaigns    = campaigns.filter(is_active=True).count()

    # Клики по дням (общий график)
    daily_qs = (
        AdClick.objects
        .filter(timestamp__gte=cutoff)
        .annotate(day=TruncDate('timestamp'))
        .values('day')
        .annotate(cnt=Count('id'))
        .order_by('day')
    )
    daily_map = {r['day']: r['cnt'] for r in daily_qs}
    chart_labels = []
    chart_values = []
    for i in range(days - 1, -1, -1):
        d = timezone.localdate() - timedelta(days=i)
        chart_labels.append(d.strftime('%d.%m'))
        chart_values.append(daily_map.get(d, 0))

    # Статистика по каждой кампании
    rows = []
    for camp in campaigns:
        clicks_period = camp.clicks.filter(timestamp__gte=cutoff).count()
        clicks_all    = camp.clicks.count()
        daily_camp = {
            r['day']: r['cnt']
            for r in (
                camp.clicks
                .filter(timestamp__gte=cutoff)
                .annotate(day=TruncDate('timestamp'))
                .values('day')
                .annotate(cnt=Count('id'))
            )
        }
        rows.append({
            'campaign':      camp,
            'clicks_period': clicks_period,
            'clicks_all':    clicks_all,
            'sparkline':     _sparkline_svg(daily_camp, days=min(days, 30)),
        })

    rows.sort(key=lambda r: r['clicks_period'], reverse=True)

    return {
        'title':               'Дашборд рекламных кампаний',
        'campaigns':           rows,
        'total_clicks_period': total_clicks_period,
        'total_clicks_all':    total_clicks_all,
        'active_campaigns':    active_campaigns,
        'chart_labels_json':   json.dumps(chart_labels),
        'chart_values_json':   json.dumps(chart_values),
        'days':                days,
        'periods':             periods,
        'has_permission':      True,
    }


# ── Admin классы ───────────────────────────────────────────────────────────

@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    list_display  = ('name', 'source_badge', 'utm_medium', 'col_7d',
                     'col_30d', 'col_total', 'copy_link_btn', 'is_active')
    list_filter   = ('is_active', 'utm_source', 'utm_medium')
    search_fields = ('name', 'utm_campaign', 'code')
    readonly_fields = ('code', 'tracking_link_field', 'stats_field')
    fieldsets = (
        ('Кампания', {
            'fields': ('name', 'is_active'),
        }),
        ('UTM-параметры', {
            'fields': ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content'),
            'description': 'Эти параметры автоматически добавятся в ссылку назначения.',
        }),
        ('Назначение', {
            'fields': ('destination',),
        }),
        ('Ваша рекламная ссылка', {
            'fields': ('tracking_link_field',),
            'description': 'Используйте эту ссылку в рекламе. Она записывает клики и перенаправляет на сайт.',
        }),
        ('Статистика', {
            'fields': ('stats_field',),
            'classes': ('collapse',),
        }),
        ('Технические данные', {
            'fields': ('code',),
            'classes': ('collapse',),
        }),
    )

    # ── List columns ──────────────────────────────────────────────────────

    @admin.display(description='Источник')
    def source_badge(self, obj):
        icon = _SOURCE_ICON.get(obj.utm_source, '🔗')
        label = obj.get_utm_source_display()
        return format_html('<span title="{}">{} {}</span>', label, icon, label)

    @admin.display(description='7 дней')
    def col_7d(self, obj):
        n = obj.clicks_7d
        color = '#4a7c59' if n > 0 else '#999'
        return format_html('<b style="color:{}">{}</b>', color, n)

    @admin.display(description='30 дней')
    def col_30d(self, obj):
        return obj.clicks_30d

    @admin.display(description='Всего')
    def col_total(self, obj):
        return obj.total_clicks

    @admin.display(description='Ссылка')
    def copy_link_btn(self, obj):
        if not obj.pk:
            return '—'
        path = obj.get_tracking_path()
        return format_html(
            '<button type="button" '
            'style="padding:3px 10px;font-size:12px;cursor:pointer;'
            'border:1px solid #ccc;border-radius:4px;background:#f8f8f8" '
            'onclick="navigator.clipboard.writeText(\'https://tlpn.shop{}\').'
            'then(()=>{{this.textContent=\'✓ Скопировано\';'
            'setTimeout(()=>this.textContent=\'📋 Копировать\',1500)}})">'
            '📋 Копировать</button>',
            path,
        )

    # ── Readonly fields in edit form ──────────────────────────────────────

    @admin.display(description='Ссылка для рекламы')
    def tracking_link_field(self, obj):
        if not obj.pk:
            return mark_safe('<i style="color:#999">Сохраните кампанию — ссылка появится здесь</i>')
        full = f'https://tlpn.shop{obj.get_tracking_path()}'
        dest = obj.get_destination_with_utm()
        return format_html(
            '''
            <div style="background:#f0f7f2;border:2px solid #4a7c59;border-radius:8px;padding:16px;margin:4px 0">
              <div style="font-size:13px;color:#666;margin-bottom:6px">📎 Короткая ссылка для рекламы:</div>
              <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
                <code id="ad-link-{pk}" style="font-size:16px;font-weight:bold;color:#4a7c59;
                      background:#fff;padding:8px 14px;border-radius:6px;border:1px solid #4a7c59;
                      word-break:break-all">{full}</code>
                <button type="button"
                  onclick="navigator.clipboard.writeText('{full}').then(()=>{{
                    this.textContent='✓ Скопировано!';
                    this.style.background='#4a7c59';this.style.color='#fff';
                    setTimeout(()=>{{this.textContent='📋 Скопировать';
                    this.style.background='';this.style.color=''}},2000)
                  }})"
                  style="padding:8px 18px;border:2px solid #4a7c59;border-radius:6px;
                         cursor:pointer;font-size:14px;font-weight:600;white-space:nowrap">
                  📋 Скопировать
                </button>
              </div>
              <div style="font-size:12px;color:#888;margin-top:8px">
                Перенаправляет на: <code style="color:#555">{dest}</code>
              </div>
            </div>
            ''',
            pk=obj.pk, full=full, dest=dest,
        )

    @admin.display(description='Статистика кликов')
    def stats_field(self, obj):
        if not obj.pk or obj.total_clicks == 0:
            return mark_safe('<i style="color:#999">Кликов пока нет</i>')
        now = timezone.now()
        rows_html = ''
        for days, label in [(1, 'Сегодня'), (7, '7 дней'), (30, '30 дней'), (None, 'Всего')]:
            if days:
                cnt = obj.clicks.filter(timestamp__gte=now - timedelta(days=days)).count()
            else:
                cnt = obj.total_clicks
            rows_html += (
                f'<tr><td style="padding:4px 12px 4px 0;color:#666">{label}</td>'
                f'<td style="font-weight:600;color:#4a7c59">{cnt}</td></tr>'
            )
        return mark_safe(f'<table style="border-collapse:collapse">{rows_html}</table>')

    # ── Custom URL: dashboard ─────────────────────────────────────────────

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view),
                 name='ads_dashboard'),
        ]
        return custom + urls

    def dashboard_view(self, request):
        ctx = _build_dashboard_context(request)
        ctx.update(self.admin_site.each_context(request))
        return TemplateResponse(request, 'admin/ads/dashboard.html', ctx)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['dashboard_url'] = 'admin:ads_dashboard'
        return super().changelist_view(request, extra_context=extra_context)
