from collections.abc import Mapping

from rest_framework import serializers

from .models import CriterionLevel, Rubric, RubricCriterion
from .services import rubric_is_in_use


class CriterionLevelSerializer(serializers.ModelSerializer[CriterionLevel]):
    """Serializer for criterion levels."""

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = CriterionLevel
        fields = ["id", "order", "score", "descriptor"]
        read_only_fields = ["id"]


class RubricCriterionSerializer(serializers.ModelSerializer[RubricCriterion]):
    """Serializer for rubric criteria with nested levels."""

    levels = CriterionLevelSerializer(many=True, read_only=True)

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = RubricCriterion
        fields = ["id", "name", "order", "levels"]
        read_only_fields = ["id"]


# rejects the old "title" field name, clients should use "name" instead
class RejectLegacyTitleFieldMixin:
    """Reject deprecated `title` request keys after the name-field hard cut."""

    def to_internal_value(self, data: object) -> object:
        if isinstance(data, Mapping) and "title" in data:
            raise serializers.ValidationError(
                {"title": ["This field is not supported. Use 'name'."]}
            )
        return super().to_internal_value(data)


class RubricSerializer(
    RejectLegacyTitleFieldMixin, serializers.ModelSerializer[Rubric]
):
    """Serializer for rubrics with nested criteria."""

    criteria = RubricCriterionSerializer(many=True, read_only=True)
    in_use = serializers.SerializerMethodField()

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = Rubric
        fields = [
            "id",
            "name",
            "description",
            "criteria",
            "in_use",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "in_use",
            "created_at",
            "updated_at",
        ]

    def get_in_use(self, obj: Rubric) -> bool:
        return rubric_is_in_use(obj)


class RubricListSerializer(serializers.ModelSerializer[Rubric]):
    """Serializer for rubric list (without nested criteria)."""

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = Rubric
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class RubricTemplateSummarySerializer(serializers.Serializer[dict[str, object]]):
    key = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    criteria_count = serializers.IntegerField()
    level_pattern = serializers.ListField(child=serializers.IntegerField())


class RubricTemplateInstantiateSerializer(
    RejectLegacyTitleFieldMixin, serializers.Serializer[dict[str, str]]
):
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)


class RubricDuplicateSerializer(
    RejectLegacyTitleFieldMixin, serializers.Serializer[dict[str, str]]
):
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)


class RubricStructureLevelSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField(required=False)
    order = serializers.IntegerField()
    score = serializers.IntegerField()
    descriptor = serializers.CharField(allow_blank=False)


class RubricStructureCriterionSerializer(serializers.Serializer[dict[str, object]]):
    id = serializers.UUIDField(required=False)
    name = serializers.CharField(allow_blank=False, max_length=255)
    order = serializers.IntegerField()
    levels = RubricStructureLevelSerializer(many=True, allow_empty=False)

    def validate_levels(
        self, levels: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        scores: list[int] = [int(level["score"]) for level in levels]
        if len(scores) != len(set(scores)):
            raise serializers.ValidationError(
                "Level scores must be unique within each criterion."
            )
        return levels


class RubricStructureSerializer(
    RejectLegacyTitleFieldMixin, serializers.Serializer[dict[str, object]]
):
    name = serializers.CharField(allow_blank=False, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    base_updated_at = serializers.DateTimeField()
    criteria = RubricStructureCriterionSerializer(many=True, allow_empty=False)
