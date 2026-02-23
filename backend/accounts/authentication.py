from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication class that reads tokens from HTTP-only cookies.
    Falls back to Authorization header if cookie is not present.
    """

    def authenticate(self, request):
        # Try to get token from cookie first
        raw_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)

        if raw_token is None:
            # Fall back to Authorization header (standard Bearer token)
            return super().authenticate(request)

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
