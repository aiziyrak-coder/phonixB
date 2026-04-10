"""HttpOnly JWT cookies (optional; JSON body tokens remain for SPA compatibility)."""

from django.conf import settings


def attach_jwt_cookies(response, access_token: str, refresh_token: str):
    if not getattr(settings, 'JWT_USE_HTTPONLY_COOKIES', False):
        return response
    if not access_token or not refresh_token:
        return response
    secure = not settings.DEBUG
    max_age_access = int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds())
    max_age_refresh = int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())
    name_access = getattr(settings, 'JWT_ACCESS_COOKIE_NAME', 'access')
    name_refresh = getattr(settings, 'JWT_REFRESH_COOKIE_NAME', 'refresh')
    common = {
        'httponly': True,
        'secure': secure,
        'samesite': 'Lax',
        'path': '/',
    }
    domain = getattr(settings, 'JWT_COOKIE_DOMAIN', None)
    if domain:
        common['domain'] = domain
    response.set_cookie(name_access, access_token, max_age=max_age_access, **common)
    response.set_cookie(name_refresh, refresh_token, max_age=max_age_refresh, **common)
    return response


def clear_jwt_cookies(response):
    name_access = getattr(settings, 'JWT_ACCESS_COOKIE_NAME', 'access')
    name_refresh = getattr(settings, 'JWT_REFRESH_COOKIE_NAME', 'refresh')
    common = {'path': '/', 'samesite': 'Lax'}
    domain = getattr(settings, 'JWT_COOKIE_DOMAIN', None)
    if domain:
        common['domain'] = domain
    response.delete_cookie(name_access, **common)
    response.delete_cookie(name_refresh, **common)
    return response
