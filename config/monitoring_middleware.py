"""
So‘rovlarni kuzatish: X-Request-ID, vaqtinchalik log (JSON yoki matn).
"""

import json
import logging
import time
import uuid

from django.conf import settings

logger = logging.getLogger('phoenix.request')

_SKIP_PREFIXES = (
    '/health',
    '/metrics',
    '/static/',
    '/favicon',
)


def _should_skip_path(path: str) -> bool:
    for p in _SKIP_PREFIXES:
        if path.startswith(p):
            return True
    return False


class RequestMonitoringMiddleware:
    """X-Request-ID qo‘shadi; so‘rov loglari ixtiyoriy (MONITORING_LOG_REQUESTS)."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'MONITORING_LOG_REQUESTS', True)
        self.use_json = getattr(settings, 'MONITORING_LOG_JSON', False)

    def __call__(self, request):
        rid = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        request.request_id = rid

        if _should_skip_path(request.path):
            response = self.get_response(request)
            response['X-Request-ID'] = rid
            return response

        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000.0
        response['X-Request-ID'] = rid

        if self.enabled:
            payload = {
                'type': 'http_request',
                'request_id': rid,
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': round(duration_ms, 2),
            }
            u = getattr(request, 'user', None)
            if u is not None and getattr(u, 'is_authenticated', False):
                payload['user_id'] = str(u.pk)
            if self.use_json:
                logger.info(json.dumps(payload, ensure_ascii=False))
            else:
                logger.info(
                    '%(method)s %(path)s %(status_code)s %(duration_ms).2fms id=%(request_id)s',
                    payload,
                )
        return response
