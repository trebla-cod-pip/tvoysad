"""
python manage.py export_user_log --uid=<uid> [--format=json|csv]
                                  [--from=YYYY-MM-DD] [--to=YYYY-MM-DD]
                                  [--output=<file>]
"""
import csv
import json
import sys
from datetime import datetime, timezone

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from activity.models import ActivityLog


def _serialize(log: ActivityLog) -> dict:
    return {
        'id':               log.pk,
        'uid':              log.uid,
        'session_key':      log.session_key,
        'ip_address':       log.ip_address,
        'timestamp':        log.timestamp.isoformat(),
        'method':           log.method,
        'path':             log.path,
        'query_string':     log.query_string,
        'status_code':      log.status_code,
        'response_time_ms': log.response_time_ms,
        'referrer':         log.referrer,
        'user_agent':       log.user_agent,
        'event_type':       log.event_type,
        'user_id':          log.user_id,
    }


FIELDS = list(_serialize(ActivityLog()).keys()) if False else [
    'id', 'uid', 'session_key', 'ip_address', 'timestamp',
    'method', 'path', 'query_string', 'status_code', 'response_time_ms',
    'referrer', 'user_agent', 'event_type', 'user_id',
]


class Command(BaseCommand):
    help = 'Экспортировать лог активности пользователя по UID'

    def add_arguments(self, parser):
        parser.add_argument('--uid',    required=True, help='UID посетителя (16 символов)')
        parser.add_argument('--format', default='json', choices=['json', 'csv'],
                            dest='fmt', help='Формат вывода: json или csv (по умолчанию json)')
        parser.add_argument('--from',   dest='date_from', default=None,
                            help='Фильтр с даты YYYY-MM-DD')
        parser.add_argument('--to',     dest='date_to',   default=None,
                            help='Фильтр до даты YYYY-MM-DD')
        parser.add_argument('--output', dest='output',    default=None,
                            help='Путь к файлу (по умолчанию stdout)')

    def handle(self, *args, **options):
        uid = options['uid']
        fmt = options['fmt']

        qs = ActivityLog.objects.filter(uid=uid).order_by('timestamp')

        if options['date_from']:
            d = parse_date(options['date_from'])
            if d is None:
                raise CommandError('Неверный формат --from, ожидается YYYY-MM-DD')
            qs = qs.filter(timestamp__date__gte=d)

        if options['date_to']:
            d = parse_date(options['date_to'])
            if d is None:
                raise CommandError('Неверный формат --to, ожидается YYYY-MM-DD')
            qs = qs.filter(timestamp__date__lte=d)

        count = qs.count()
        if count == 0:
            self.stderr.write(self.style.WARNING(f'Записей для uid={uid} не найдено'))
            return

        output_path = options['output']
        out = open(output_path, 'w', encoding='utf-8', newline='') if output_path else sys.stdout

        try:
            if fmt == 'json':
                rows = [_serialize(log) for log in qs.iterator()]
                json.dump(rows, out, ensure_ascii=False, indent=2)
                out.write('\n')
            else:
                writer = csv.DictWriter(out, fieldnames=FIELDS)
                writer.writeheader()
                for log in qs.iterator():
                    writer.writerow(_serialize(log))
        finally:
            if output_path:
                out.close()

        self.stderr.write(self.style.SUCCESS(
            f'Экспортировано {count} записей для uid={uid} [{fmt}]'
        ))
