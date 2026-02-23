from django.conf import settings
from drf_spectacular.utils import (
    OpenApiExample,
    extend_schema,  # type: ignore[reportUnknownVariableType]
    extend_schema_view,  # type: ignore[reportUnknownVariableType]
    inline_serializer,  # type: ignore[reportUnknownVariableType]
)
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from instagrader.schema import error_responses

from .models import User
from .serializers import ChangePasswordSerializer, RegisterSerializer, UserSerializer
from .types import AuthenticatedRequest


@extend_schema_view(
    create=extend_schema(
        tags=["auth"],
        operation_id="auth_register",
        description="Register a new teacher account.",
        request=RegisterSerializer,
        responses={
            201: RegisterSerializer,
            **error_responses(400),
        },
        examples=[
            OpenApiExample(
                "Email already exists",
                value={"email": ["A user with this email already exists."]},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Passwords don't match",
                value={"password_confirm": ["Passwords don't match."]},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    ),
)
class RegisterView(generics.CreateAPIView[User]):
    """Register a new teacher account."""

    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


@extend_schema_view(
    retrieve=extend_schema(
        tags=["auth"],
        operation_id="auth_profile_retrieve",
        description="Get the current user's profile.",
        responses={
            200: UserSerializer,
            **error_responses(401),
        },
    ),
    partial_update=extend_schema(
        tags=["auth"],
        operation_id="auth_profile_partial_update",
        description="Update the current user's profile. Only full_name can be changed.",
        request=UserSerializer,
        responses={
            200: UserSerializer,
            **error_responses(400, 401),
        },
    ),
    update=extend_schema(
        tags=["auth"],
        operation_id="auth_profile_update",
        description="Replace the current user's profile.",
        request=UserSerializer,
        responses={
            200: UserSerializer,
            **error_responses(400, 401),
        },
    ),
)
class UserProfileView(generics.RetrieveUpdateAPIView[User]):
    """Get or update current user profile."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self) -> User:
        return self.request.user  # type: ignore[return-value]


class ChangePasswordView(APIView):
    """Change user password."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        operation_id="auth_change_password",
        description="Change the authenticated user's password.",
        request=ChangePasswordSerializer,
        responses={
            200: inline_serializer(
                name="ChangePasswordSuccess",
                fields={
                    "detail": serializers.CharField(
                        default="Password changed successfully."
                    )
                },
            ),
            **error_responses(400, 401),
        },
        examples=[
            OpenApiExample(
                "Incorrect old password",
                value={"old_password": ["Old password is incorrect."]},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request: AuthenticatedRequest) -> Response:
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        new_password: str = serializer.validated_data["new_password"]
        request.user.set_password(new_password)
        request.user.save()

        return Response(
            {"detail": "Password changed successfully."}, status=status.HTTP_200_OK
        )


class CookieTokenObtainPairView(TokenObtainPairView):
    """
    Custom login view that sets JWT tokens as HTTP-only cookies
    instead of returning them in the response body.
    """

    def finalize_response(self, request, response, *args, **kwargs):
        if response.data.get("access"):
            response.set_cookie(
                key=settings.JWT_AUTH_COOKIE,
                value=response.data["access"],
                max_age=int(
                    settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
                ),
                secure=settings.JWT_AUTH_SECURE,
                httponly=True,
                samesite=settings.JWT_AUTH_SAMESITE,
            )
            response.set_cookie(
                key=settings.JWT_AUTH_REFRESH_COOKIE,
                value=response.data["refresh"],
                max_age=int(
                    settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
                ),
                secure=settings.JWT_AUTH_SECURE,
                httponly=True,
                samesite=settings.JWT_AUTH_SAMESITE,
            )
            # Remove tokens from response body for security
            del response.data["access"]
            del response.data["refresh"]
        return super().finalize_response(request, response, *args, **kwargs)


class CookieTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view that reads the refresh token from cookies
    and sets the new access token as an HTTP-only cookie.
    """

    serializer_class = None  # Will be set dynamically

    def post(self, request, *args, **kwargs):
        # Read refresh token from cookie
        refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)

        # Prepare data for serializer
        data = {}
        if refresh_token:
            data["refresh"] = refresh_token
        elif request.data.get("refresh"):
            data["refresh"] = request.data["refresh"]

        # If no refresh token provided, return 401
        if not data.get("refresh"):
            return Response(
                {"detail": "Refresh token not provided"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Create serializer with cookie data
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer
        from rest_framework_simplejwt.exceptions import TokenError

        try:
            serializer = TokenRefreshSerializer(data=data)
            serializer.is_valid(raise_exception=True)
        except TokenError:
            # Return 401 for invalid tokens
            return Response(
                {"detail": "Token is invalid or expired"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Build response
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)

        # Set access token as cookie
        if serializer.validated_data.get("access"):
            response.set_cookie(
                key=settings.JWT_AUTH_COOKIE,
                value=serializer.validated_data["access"],
                max_age=int(
                    settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()
                ),
                secure=settings.JWT_AUTH_SECURE,
                httponly=True,
                samesite=settings.JWT_AUTH_SAMESITE,
            )
            # Remove token from response body
            del response.data["access"]

        return response


class LogoutView(APIView):
    """
    Logout view that clears the JWT auth cookies.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["auth"],
        operation_id="auth_logout",
        description="Logout by clearing authentication cookies.",
        request=None,
        responses={
            200: inline_serializer(
                name="LogoutSuccess",
                fields={"detail": serializers.CharField(default="Successfully logged out.")},
            ),
        },
    )
    def post(self, request):
        response = Response(
            {"detail": "Successfully logged out."}, status=status.HTTP_200_OK
        )
        response.delete_cookie(settings.JWT_AUTH_COOKIE)
        response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE)
        return response
