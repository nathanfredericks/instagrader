from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CriterionScore, GradingResult
from .serializers import CriterionScoreSerializer, GradingResultSerializer


class EssayDetailView(APIView):
    """Get essay with extracted text."""

    def get(self, request, essay_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class EssayDeleteView(APIView):
    """Remove essay from assignment."""

    def delete(self, request, essay_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class EssayGradingView(APIView):
    """Get or update grading result for essay."""

    def get(self, request, essay_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )

    def patch(self, request, essay_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class EssayGradingApproveView(APIView):
    """Approve grading result."""

    def post(self, request, essay_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )
