from rest_framework import serializers

from .models import CriterionScore, GradingResult


class CriterionScoreSerializer(serializers.ModelSerializer):
    """Serializer for criterion scores."""

    class Meta:
        model = CriterionScore
        fields = [
            'id',
            'criterion',
            'level',
            'feedback',
            'teacher_level',
            'teacher_feedback',
        ]
        read_only_fields = ['id', 'criterion', 'level', 'feedback']


class GradingResultSerializer(serializers.ModelSerializer):
    """Serializer for grading results with nested criterion scores."""

    criterion_scores = CriterionScoreSerializer(many=True, read_only=True)

    class Meta:
        model = GradingResult
        fields = [
            'id',
            'essay',
            'teacher_approved',
            'approved_at',
            'criterion_scores',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'essay',
            'teacher_approved',
            'approved_at',
            'created_at',
            'updated_at',
        ]
