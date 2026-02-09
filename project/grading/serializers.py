from rest_framework import serializers

from .models import CriterionScore, GradingResult


class CriterionScoreSerializer(serializers.ModelSerializer[CriterionScore]):
    """Serializer for criterion scores."""

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = CriterionScore
        fields = [
            "id",
            "criterion",
            "level",
            "feedback",
            "teacher_level",
            "teacher_feedback",
        ]
        read_only_fields = ["id", "criterion", "level", "feedback"]


class GradingResultSerializer(serializers.ModelSerializer[GradingResult]):
    """Serializer for grading results with nested criterion scores."""

    criterion_scores = CriterionScoreSerializer(many=True, read_only=True)

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = GradingResult
        fields = [
            "id",
            "essay",
            "teacher_approved",
            "approved_at",
            "criterion_scores",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "essay",
            "teacher_approved",
            "approved_at",
            "created_at",
            "updated_at",
        ]
