"""Custom DRF throttles for expensive or sensitive endpoints."""

from rest_framework.throttling import SimpleRateThrottle


class PlagiarismActionThrottle(SimpleRateThrottle):
    """Rate limit only for ArticleViewSet.check_plagiarism (Gemini)."""

    scope = 'gemini'

    def get_cache_key(self, request, view):
        if getattr(view, 'action', None) != 'check_plagiarism':
            return None
        ident = self.get_ident(request)
        if not ident:
            return None
        return self.cache_format % {'scope': self.scope, 'ident': ident}
