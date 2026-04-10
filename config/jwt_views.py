from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from .jwt_cookies import attach_jwt_cookies


class CookieTokenRefreshView(TokenRefreshView):
    """Body yoki HttpOnly refresh cookie orqali yangilash; javobda cookie yangilanadi."""

    def post(self, request, *args, **kwargs):
        data = dict(request.data) if hasattr(request.data, 'keys') else {}
        if not data.get('refresh') and getattr(settings, 'JWT_USE_HTTPONLY_COOKIES', False):
            c = request.COOKIES.get(getattr(settings, 'JWT_REFRESH_COOKIE_NAME', 'refresh'))
            if c:
                data = {**data, 'refresh': c}
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        access = validated['access']
        new_refresh = validated.get('refresh')
        out = {'access': access}
        if new_refresh is not None:
            out['refresh'] = new_refresh
        response = Response(out, status=status.HTTP_200_OK)
        if getattr(settings, 'JWT_USE_HTTPONLY_COOKIES', False) and access:
            refresh_for_cookie = new_refresh if new_refresh is not None else data.get('refresh')
            if refresh_for_cookie:
                attach_jwt_cookies(response, access, refresh_for_cookie)
        return response
