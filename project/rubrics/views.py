from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CriterionLevel, Rubric, RubricCriterion
from .serializers import (
    CriterionLevelSerializer,
    RubricCriterionSerializer,
    RubricListSerializer,
    RubricSerializer,
)


class RubricListCreateView(APIView):
    """List user's rubrics or create a new rubric."""

    def get(self, request):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )

    def post(self, request):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class RubricDetailView(APIView):
    """Get, update, or delete a rubric."""

    def get(self, request, rubric_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )

    def patch(self, request, rubric_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )

    def delete(self, request, rubric_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class CriterionListCreateView(APIView):
    """Add a criterion to a rubric."""

    def post(self, request, rubric_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class CriterionDetailView(APIView):
    """Update or delete a criterion."""

    def patch(self, request, rubric_id, criterion_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )

    def delete(self, request, rubric_id, criterion_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class CriterionReorderView(APIView):
    """Reorder criteria within a rubric."""

    def post(self, request, rubric_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class LevelListCreateView(APIView):
    """Add a level to a criterion."""

    def post(self, request, rubric_id, criterion_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class LevelDetailView(APIView):
    """Update or delete a level."""

    def patch(self, request, rubric_id, criterion_id, level_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )

    def delete(self, request, rubric_id, criterion_id, level_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )
