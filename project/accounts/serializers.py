from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.request import Request

from .models import User


class UserSerializer(serializers.ModelSerializer[User]):
    """Serializer for user profile."""

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = User
        fields = ["id", "email", "full_name", "created_at", "updated_at"]
        read_only_fields = ["id", "email", "created_at", "updated_at"]


class RegisterSerializer(serializers.ModelSerializer[User]):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = User
        fields = ["email", "full_name", "password", "password_confirm"]

    def validate(self, attrs: dict[str, str]) -> dict[str, str]:
        email = attrs.get("email")
        if email:
            normalized_email = email.strip().lower()
            if User.objects.filter(email__iexact=normalized_email).exists():
                raise serializers.ValidationError(
                    {"email": "A user with this email already exists."}
                )
            attrs["email"] = normalized_email
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords don't match."}
            )
        return attrs

    def create(self, validated_data: dict[str, str]) -> User:
        validated_data.pop("password_confirm")
        # Use email as username
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
