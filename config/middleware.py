"""Production helpers: admin brute-force mitigation, optional API security headers."""

import logging

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)


class AdminLoginRateLimitMiddleware:
    """
    Limit failed POST /admin/login/ per IP (default 30 failures / 15 min).
    Muvaffaqiyatli kirishda hisoblagich tiklanadi.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.limit = int(getattr(settings, 'ADMIN_LOGIN_RATELIMIT_PER_IP', 30))
        self.window_sec = int(getattr(settings, 'ADMIN_LOGIN_RATELIMIT_WINDOW_SEC', 900))

    def __call__(self, request):
        path = request.path.rstrip('/')
        if path != '/admin/login' or request.method != 'POST' or settings.DEBUG:
            return self.get_response(request)

        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get(
            'REMOTE_ADDR', 'unknown'
        )
        key = f'admin_login_fail:{ip}'

        n = cache.get(key, 0)
        if n >= self.limit:
            logger.warning('Admin login rate limit exceeded for IP %s', ip)
            return HttpResponseForbidden('Too many failed login attempts. Try again later.')

        response = self.get_response(request)

        if response.status_code in (302, 303) and response.get('Location', '').rstrip('/').endswith('/admin'):
            cache.delete(key)
        elif response.status_code == 200:
            cache.set(key, n + 1, self.window_sec)

        return response


class ApiSecurityHeadersMiddleware:
    """Light headers for JSON API (admin HTML not heavily restricted here)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.DEBUG:
            return response
        if request.path.startswith('/admin'):
            return response
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        csp = getattr(settings, 'DJANGO_API_CSP', '') or ''
        if csp.strip():
            response['Content-Security-Policy'] = csp.strip()
        return response
