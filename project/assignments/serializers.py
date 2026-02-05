from rest_framework import serializers

from .models import Assignment, Essay


class EssaySerializer(serializers.ModelSerializer):
    """Serializer for essay details."""

    class Meta:
        model = Essay
        fields = [
            'id',
            'student_name',
            'original_file',
            'extracted_text',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'extracted_text', 'created_at', 'updated_at']


class EssayListSerializer(serializers.ModelSerializer):
    """Serializer for essay list (without extracted text)."""

    class Meta:
        model = Essay
        fields = ['id', 'student_name', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']


class AssignmentSerializer(serializers.ModelSerializer):
    """Serializer for assignment details."""

    essays = EssayListSerializer(many=True, read_only=True)

    class Meta:
        model = Assignment
        fields = [
            'id',
            'rubric',
            'title',
            'prompt',
            'source_text',
            'status',
            'essays',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']


class AssignmentListSerializer(serializers.ModelSerializer):
    """Serializer for assignment list."""

    essay_count = serializers.IntegerField(source='essays.count', read_only=True)

    class Meta:
        model = Assignment
        fields = ['id', 'title', 'status', 'essay_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']
