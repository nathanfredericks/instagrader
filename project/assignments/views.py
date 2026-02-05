from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Assignment, Essay
from .serializers import (
    AssignmentListSerializer,
    AssignmentSerializer,
    EssayListSerializer,
    EssaySerializer,
)


class AssignmentListCreateView(APIView):
    """List user's assignments or create a new assignment."""

    def get(self, request):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )

    def post(self, request):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class AssignmentDetailView(APIView):
    """Get, update, or delete an assignment."""

    def get(self, request, assignment_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )

    def patch(self, request, assignment_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )

    def delete(self, request, assignment_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class AssignmentUploadView(APIView):
    """Upload essays (zip file or individual) to an assignment."""

    def post(self, request, assignment_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class AssignmentEssaysView(APIView):
    """List essays in an assignment."""

    def get(self, request, assignment_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class AssignmentExportCSVView(APIView):
    """Export grades to CSV."""

    def get(self, request, assignment_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class AssignmentExportPDFView(APIView):
    """Export essay feedback as PDF."""

    def get(self, request, assignment_id, essay_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class EssayDetailView(APIView):
    """Get or delete an essay."""

    def get(self, request, essay_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )

    def delete(self, request, essay_id):
        return Response(
            {'detail': 'Not implemented'}, status=status.HTTP_501_NOT_IMPLEMENTED
        )
