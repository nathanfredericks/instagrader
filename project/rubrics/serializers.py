from rest_framework import serializers

from .models import CriterionLevel, Rubric, RubricCriterion


class CriterionLevelSerializer(serializers.ModelSerializer):
    """Serializer for criterion levels."""

    class Meta:
        model = CriterionLevel
        fields = ['id', 'score', 'descriptor']
        read_only_fields = ['id']


class RubricCriterionSerializer(serializers.ModelSerializer):
    """Serializer for rubric criteria with nested levels."""

    levels = CriterionLevelSerializer(many=True, read_only=True)

    class Meta:
        model = RubricCriterion
        fields = ['id', 'name', 'order', 'levels']
        read_only_fields = ['id']


class RubricSerializer(serializers.ModelSerializer):
    """Serializer for rubrics with nested criteria."""

    criteria = RubricCriterionSerializer(many=True, read_only=True)

    class Meta:
        model = Rubric
        fields = ['id', 'title', 'description', 'criteria', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RubricListSerializer(serializers.ModelSerializer):
    """Serializer for rubric list (without nested criteria)."""

    class Meta:
        model = Rubric
        fields = ['id', 'title', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
