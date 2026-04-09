from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication class that reads tokens from HTTP-only cookies.
    Falls back to Authorization header if cookie is not present.
    """

    def authenticate(self, request):
        # tries cookie first for browser clients, falls back to authorization header for api consumers
        raw_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)

        if raw_token is None:
            return super().authenticate(request)

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
