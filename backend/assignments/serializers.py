from rest_framework import serializers
from rest_framework.request import Request

from rubrics.models import Rubric

from .models import Assignment, Essay


class EssaySerializer(serializers.ModelSerializer[Essay]):
    """Serializer for essay details."""

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = Essay
        fields = [
            "id",
            "file_name",
            "original_file",
            "extracted_text",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "extracted_text", "created_at", "updated_at"]


class EssayListSerializer(serializers.ModelSerializer[Essay]):
    """Serializer for essay list (without extracted text)."""

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = Essay
        fields = ["id", "file_name", "status", "created_at"]
        read_only_fields = ["id", "created_at"]


class AssignmentSerializer(serializers.ModelSerializer[Assignment]):
    """Serializer for assignment details."""

    essays = EssayListSerializer(many=True, read_only=True)

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = Assignment
        fields = [
            "id",
            "rubric",
            "title",
            "prompt",
            "source_text",
            "status",
            "essays",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def validate_rubric(self, value: Rubric) -> Rubric:
        request: Request | None = self.context.get("request")
        if request and value.user != request.user:
            raise serializers.ValidationError("You can only use your own rubrics.")
        return value


class AssignmentListSerializer(serializers.ModelSerializer[Assignment]):
    """Serializer for assignment list."""

    essay_count = serializers.IntegerField(read_only=True)

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = Assignment
        fields = ["id", "title", "status", "essay_count", "created_at", "updated_at"]
        read_only_fields = ["id", "status", "created_at", "updated_at"]
