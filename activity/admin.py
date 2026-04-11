import json
from datetime import timedelta

from django.contrib import admin
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate, TruncHour
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import ActivityLog


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

EVENT_COLORS = {
    'pageview': '#4CAF50',
    'api':      '#2196F3',
    'auth':     '#FF9800',
    'form':     '#9C27B0',
    'error':    '#f44336',
    'other':    '#9E9E9E',
}

STATUS_COLOR = {
    '2': '#4CAF50',   # 2xx
    '3': '#FF9800',   # 3xx
    '4': '#F44336',   # 4xx
    '5': '#B71C1C',   # 5xx
}


def _status_color(code):
    return STATUS_COLOR.get(str(code)[0], '#9E9E9E')


def _build_dashboard_context(request, admin_site):
    period = int(request.GET.get('period', 1))
    period = period if period in (1, 7, 30) else 1

    now  = timezone.now()
    start = now - timedelta(days=period)
    qs = ActivityLog.objects.filter(timestamp__gte=start)

    # ── KPI ──────────────────────────────────────────────────────────────────
    total    = qs.count()
    unique   = qs.values('uid').distinct().count()
    avg_ms   = round(qs.aggregate(a=Avg('response_time_ms'))['a'] or 0)
    err_cnt  = qs.filter(status_code__gte=500).count()
    err_rate = round(err_cnt / total * 100, 1) if total else 0

    # ── Timeline ─────────────────────────────────────────────────────────────
    if period == 1:
        tl_qs = (
            qs.annotate(t=TruncHour('timestamp'))
              .values('t').annotate(n=Count('id')).order_by('t')
        )
        tl_labels = [r['t'].strftime('%H:%M') for r in tl_qs]
    else:
        tl_qs = (
            qs.annotate(t=TruncDate('timestamp'))
              .values('t').annotate(n=Count('id')).order_by('t')
        )
        tl_labels = [r['t'].strftime('%d.%m') for r in tl_qs]
    tl_data   = [r['n'] for r in tl_qs]

    # ── Event types ───────────────────────────────────────────────────────────
    evt_rows   = list(qs.values('event_type').annotate(n=Count('id')).order_by('-n'))
    evt_labels = [r['event_type'] for r in evt_rows]
    evt_data   = [r['n']          for r in evt_rows]
    evt_colors = [EVENT_COLORS.get(e, '#9E9E9E') for e in evt_labels]

    # ── Status codes ─────────────────────────────────────────────────────────
    sc_rows   = list(qs.values('status_code').annotate(n=Count('id')).order_by('status_code'))
    sc_labels = [str(r['status_code']) for r in sc_rows]
    sc_data   = [r['n']               for r in sc_rows]
    sc_colors = [_status_color(r['status_code']) for r in sc_rows]

    # ── Top pages ─────────────────────────────────────────────────────────────
    top_pages = list(
        qs.exclude(event_type='api')
          .values('path')
          .annotate(hits=Count('id'), avg_ms=Avg('response_time_ms'))
          .order_by('-hits')[:15]
    )
    for p in top_pages:
        p['avg_ms'] = round(p['avg_ms'] or 0)

    # ── Top visitors ─────────────────────────────────────────────────────────
    top_vis = list(
        qs.values('uid')
          .annotate(requests=Count('id'), pages=Count('path', distinct=True))
          .order_by('-requests')[:10]
    )
    # добавить ссылку фильтра на список
    for v in top_vis:
        v['filter_url'] = (
            reverse('admin:activity_activitylog_changelist') + f'?uid={v["uid"]}'
        )

    # ── Top API paths ─────────────────────────────────────────────────────────
    top_api = list(
        qs.filter(event_type='api')
          .values('path', 'method')
          .annotate(hits=Count('id'), avg_ms=Avg('response_time_ms'))
          .order_by('-hits')[:10]
    )
    for a in top_api:
        a['avg_ms'] = round(a['avg_ms'] or 0)

    # ── Traffic source: Telegram vs Web ──────────────────────────────────────
    # Telegram-пользователи всегда вызывают /api/tg/ — надёжный маркер.
    tg_uids = set(
        qs.filter(path__startswith='/api/tg/')
          .values_list('uid', flat=True)
          .distinct()
    )
    tg_req  = qs.filter(uid__in=tg_uids).count() if tg_uids else 0
    web_req = total - tg_req
    tg_vis  = len(tg_uids)
    web_vis = unique - tg_vis

    # Timeline split: TG / Web по тем же меткам что и основной график
    trunc_fn = TruncHour if period == 1 else TruncDate
    fmt      = '%H:%M'   if period == 1 else '%d.%m'

    def _tl_map(queryset):
        rows = (queryset.annotate(t=trunc_fn('timestamp'))
                        .values('t').annotate(n=Count('id')).order_by('t'))
        return {r['t'].strftime(fmt): r['n'] for r in rows}

    tg_by_t  = _tl_map(qs.filter(uid__in=tg_uids))  if tg_uids else {}
    web_by_t = _tl_map(qs.exclude(uid__in=tg_uids)) if tg_uids else _tl_map(qs)

    all_tl_labels = sorted(set(tg_by_t) | set(web_by_t))
    tl_tg_data  = [tg_by_t.get(l, 0)  for l in all_tl_labels]
    tl_web_data = [web_by_t.get(l, 0) for l in all_tl_labels]

    # ── Recent errors ─────────────────────────────────────────────────────────
    recent_errors = list(
        qs.filter(status_code__gte=400)
          .order_by('-timestamp')
          .values('timestamp', 'method', 'path', 'status_code', 'uid', 'response_time_ms')[:20]
    )

    return {
        **admin_site.each_context(request),
        'title':        'Дашборд активности',
        'period':        period,
        'start':         start,
        'now':           now,
        # KPIs
        'total':         total,
        'unique':        unique,
        'avg_ms':        avg_ms,
        'err_rate':      err_rate,
        # Traffic source
        'tg_req':   tg_req,
        'web_req':  web_req,
        'tg_vis':   tg_vis,
        'web_vis':  web_vis,
        # Charts (JSON)
        'tl_labels_json':     json.dumps(tl_labels,      ensure_ascii=False),
        'tl_data_json':       json.dumps(tl_data),
        'tl_src_labels_json': json.dumps(all_tl_labels,  ensure_ascii=False),
        'tl_tg_json':         json.dumps(tl_tg_data),
        'tl_web_json':        json.dumps(tl_web_data),
        'evt_labels_json': json.dumps(evt_labels, ensure_ascii=False),
        'evt_data_json':   json.dumps(evt_data),
        'evt_colors_json': json.dumps(evt_colors),
        'sc_labels_json':  json.dumps(sc_labels),
        'sc_data_json':    json.dumps(sc_data),
        'sc_colors_json':  json.dumps(sc_colors),
        # Tables
        'top_pages':     top_pages,
        'top_vis':       top_vis,
        'top_api':       top_api,
        'recent_errors': recent_errors,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Admin
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display   = ('timestamp', 'event_badge', 'method', 'path_short',
                      'status_badge', 'response_time_ms', 'uid', 'ip_address', 'user_id')
    list_filter    = ('event_type', 'method', 'status_code')
    search_fields  = ('uid', 'path', 'ip_address', 'user_agent')
    readonly_fields = [f.name for f in ActivityLog._meta.fields]
    ordering       = ('-timestamp',)
    date_hierarchy = 'timestamp'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['dashboard_url'] = reverse('activity_dashboard')
        return super().changelist_view(request, extra_context)

    # ── Display helpers ───────────────────────────────────────────────────────

    def path_short(self, obj):
        p = obj.path
        return p if len(p) <= 60 else p[:57] + '…'
    path_short.short_description = 'Путь'

    def event_badge(self, obj):
        color = EVENT_COLORS.get(obj.event_type, '#9E9E9E')
        labels = dict(ActivityLog.EVENT_CHOICES)
        label  = labels.get(obj.event_type, obj.event_type)
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;white-space:nowrap">{}</span>',
            color, label,
        )
    event_badge.short_description = 'Тип'

    def status_badge(self, obj):
        color = _status_color(obj.status_code)
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:12px">{}</span>',
            color, obj.status_code,
        )
    status_badge.short_description = 'Статус'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
