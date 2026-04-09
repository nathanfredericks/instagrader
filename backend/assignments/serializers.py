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
            "failure_reason",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "extracted_text", "created_at", "updated_at"]


class EssayListSerializer(serializers.ModelSerializer[Essay]):
    """Serializer for essay list (without extracted text)."""

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = Essay
        fields = ["id", "file_name", "failure_reason", "status", "created_at"]
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
            "description",
            "prompt",
            "source_text",
            "status",
            "grading_started_at",
            "grading_completed_at",
            "essays",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "grading_started_at",
            "grading_completed_at",
            "created_at",
            "updated_at",
        ]

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
        fields = [
            "id",
            "title",
            "description",
            "status",
            "essay_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]
