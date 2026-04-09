from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.validators import UniqueValidator

from .models import User


class UserSerializer(serializers.ModelSerializer[User]):
    """Serializer for user profile."""

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = User
        fields = ["id", "email", "full_name", "created_at", "updated_at"]
        read_only_fields = ["id", "email", "created_at", "updated_at"]


class RegisterSerializer(serializers.ModelSerializer[User]):
    """Serializer for user registration."""

    email = serializers.EmailField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="A user with this email already exists.",
                lookup="iexact",
            )
        ],
    )
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = User
        fields = ["email", "full_name", "password", "password_confirm"]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate(self, attrs: dict[str, str]) -> dict[str, str]:
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords don't match."}
            )
        return attrs

    def create(self, validated_data: dict[str, str]) -> User:
        validated_data.pop("password_confirm")
        # uses email as username since the app doesnt have separate usernames
        validated_data["username"] = validated_data["email"]
        user = User.objects.create_user(**validated_data)
        return user


class ChangePasswordSerializer(serializers.Serializer[dict[str, str]]):
    """Serializer for password change."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate_old_password(self, value: str) -> str:
        request: Request = self.context["request"]
        if not request.user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
