from rest_framework import serializers

from rubrics.models import CriterionLevel

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
            "teacher_review_state",
            "teacher_reviewed_at",
        ]
        read_only_fields = ["id", "criterion", "level", "feedback"]


class CriterionScoreUpdateSerializer(serializers.Serializer):
    """Serializer for updating teacher overrides on a single criterion score."""

    id = serializers.UUIDField()
    teacher_level = serializers.PrimaryKeyRelatedField(
        queryset=CriterionLevel.objects.all(),
        allow_null=True,
        required=False,
    )
    teacher_feedback = serializers.CharField(required=False, allow_blank=True)
    teacher_review_state = serializers.ChoiceField(
        choices=CriterionScore.ReviewState.choices,
        required=False,
    )


class GradingResultApproveSerializer(serializers.Serializer):
    """Optional payload for atomic criterion updates before approval."""

    criterion_scores = CriterionScoreUpdateSerializer(many=True, required=False)


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
