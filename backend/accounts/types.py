from rest_framework.request import Request

from .models import User


class AuthenticatedRequest(Request):
    """DRF Request with a properly typed `user` attribute.

    All views in this project use IsAuthenticated, so request.user
    is always the concrete User model.
    """

    user: User  # type: ignore[assignment]
