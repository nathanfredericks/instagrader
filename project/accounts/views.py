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
