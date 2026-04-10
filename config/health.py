"""
Sog‘liq tekshiruvlari va Prometheus metrics (monitoring / load balancer).

- /health/ yoki /health/live/ — jarayon tirik (DB tekshirilmaydi).
- /health/ready/ — PostgreSQL + ixtiyoriy Redis (REDIS_URL).
- /metrics/ — Prometheus text format (faqat nozik ma’lumot: versiya, up).
"""

import os
import sys
import time

import django
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

# Jarayon ishga tushgan vaqt (process lifetime)
_started_monotonic = time.monotonic()
_started_wall = time.time()


def _app_version() -> str:
    return (os.getenv('APP_VERSION') or os.getenv('GIT_REVISION') or '0.0.0').strip() or '0.0.0'


def _git_revision() -> str:
    return (os.getenv('GIT_REVISION') or os.getenv('COMMIT_SHA') or '').strip()


def _check_database():
    connection.ensure_connection()
    return 'ok'


def _check_redis():
    url = (os.getenv('REDIS_URL') or '').strip()
    if not url:
        return 'skipped', 'REDIS_URL not set'
    try:
        import redis

        client = redis.from_url(url, socket_connect_timeout=1.5, socket_timeout=1.5)
        client.ping()
        return 'ok', None
    except Exception as exc:
        return 'error', str(exc)[:240]


@require_GET
def health_live(request):
    """Liveness: jarayon javob beradi (orchestrator restart qilmasligi uchun)."""
    payload = {
        'status': 'ok',
        'service': 'phoenix-api',
        'version': _app_version(),
        'django': django.get_version(),
        'python': f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}',
    }
    rev = _git_revision()
    if rev:
        payload['revision'] = rev
    return JsonResponse(payload)


@require_GET
def health_ready(request):
    """Readiness: DB majburiy; Redis — REDIS_URL bo‘lsa tekshiriladi."""
    checks = {}
    status_ok = True

    try:
        _check_database()
        checks['database'] = {'status': 'ok'}
    except Exception as exc:
        status_ok = False
        checks['database'] = {'status': 'error', 'detail': str(exc)[:240]}

    redis_status, redis_detail = _check_redis()
    if redis_status == 'skipped':
        checks['redis'] = {'status': 'skipped', 'detail': redis_detail or ''}
    elif redis_status == 'ok':
        checks['redis'] = {'status': 'ok'}
    else:
        status_ok = False
        checks['redis'] = {'status': 'error', 'detail': redis_detail or 'unknown'}

    body = {
        'status': 'ready' if status_ok else 'unready',
        'checks': checks,
        'version': _app_version(),
    }
    return JsonResponse(body, status=200 if status_ok else 503)


@require_GET
def metrics_prometheus(request):
    """
    Minimal Prometheus exposition (PII yo‘q).
    Ko‘p worker (gunicorn) holatida har bir worker o‘z qiymatini beradi — Prometheus odatda sumlaydi yoki max tanlaydi.
    """
    secret = (os.getenv('METRICS_SECRET') or '').strip()
    if secret:
        if request.headers.get('X-Metrics-Key') != secret:
            return HttpResponse('Forbidden', status=403, content_type='text/plain')

    uptime = time.monotonic() - _started_monotonic
    ver = _app_version().replace('"', '')

    lines = [
        '# HELP phoenix_up Process is serving requests (1=yes).',
        '# TYPE phoenix_up gauge',
        'phoenix_up 1',
        '# HELP phoenix_uptime_seconds Time since worker process started.',
        '# TYPE phoenix_uptime_seconds gauge',
        f'phoenix_uptime_seconds {uptime:.3f}',
        '# HELP phoenix_info Static build labels.',
        '# TYPE phoenix_info gauge',
        f'phoenix_info{{version="{ver}"}} 1',
        '',
    ]
    return HttpResponse(''.join(lines), content_type='text/plain; version=0.0.4; charset=utf-8')
