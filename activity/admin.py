from django.contrib import admin
from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display  = ('timestamp', 'uid', 'event_type', 'method', 'path',
                     'status_code', 'response_time_ms', 'ip_address', 'user_id')
    list_filter   = ('event_type', 'method', 'status_code')
    search_fields = ('uid', 'path', 'ip_address', 'user_agent')
    readonly_fields = [f.name for f in ActivityLog._meta.fields]
    ordering      = ('-timestamp',)
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
