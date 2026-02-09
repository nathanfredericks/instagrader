from rest_framework import serializers

from .models import CriterionLevel, Rubric, RubricCriterion


class CriterionLevelSerializer(serializers.ModelSerializer[CriterionLevel]):
    """Serializer for criterion levels."""

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = CriterionLevel
        fields = ["id", "score", "descriptor"]
        read_only_fields = ["id"]


class RubricCriterionSerializer(serializers.ModelSerializer[RubricCriterion]):
    """Serializer for rubric criteria with nested levels."""

    levels = CriterionLevelSerializer(many=True, read_only=True)

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = RubricCriterion
        fields = ["id", "name", "order", "levels"]
        read_only_fields = ["id"]


class RubricSerializer(serializers.ModelSerializer[Rubric]):
    """Serializer for rubrics with nested criteria."""

    criteria = RubricCriterionSerializer(many=True, read_only=True)

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = Rubric
        fields = ["id", "title", "description", "criteria", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class RubricListSerializer(serializers.ModelSerializer[Rubric]):
    """Serializer for rubric list (without nested criteria)."""

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = Rubric
        fields = ["id", "title", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
