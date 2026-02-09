import uuid

from drf_spectacular.utils import extend_schema  # type: ignore[reportUnknownVariableType]
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.types import AuthenticatedRequest
from assignments.models import Essay
from assignments.serializers import EssaySerializer

from instagrader.schema import error_responses


class EssayDetailView(APIView):
    """Get essay with extracted text."""

    @extend_schema(
        tags=["essays"],
        operation_id="essays_essay_retrieve",
        description="Retrieve an essay with its extracted text content.",
        responses={
            200: EssaySerializer,
            **error_responses(401, 404),
        },
    )
    def get(self, request: AuthenticatedRequest, essay_id: uuid.UUID) -> Response:
        try:
            essay = Essay.objects.get(id=essay_id, assignment__user=request.user)
        except Essay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = EssaySerializer(essay)
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]


class EssayDeleteView(APIView):
    """Remove essay from assignment."""

    @extend_schema(
        tags=["essays"],
        operation_id="essays_essay_delete",
        description="Delete an essay from its assignment.",
        responses={
            204: None,
            **error_responses(401, 404),
        },
    )
    def delete(self, request: AuthenticatedRequest, essay_id: uuid.UUID) -> Response:
        try:
            essay = Essay.objects.get(id=essay_id, assignment__user=request.user)
        except Essay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        essay.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EssayGradingView(APIView):
    """Get or update grading result for essay."""

    @extend_schema(
        tags=["essays"],
        operation_id="essays_grading_retrieve",
        description="Get grading result for an essay. Not yet implemented.",
        responses={
            **error_responses(401, 501),
        },
    )
    def get(self, request: AuthenticatedRequest, essay_id: uuid.UUID) -> Response:
        return Response(
            {"detail": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED
        )

    @extend_schema(
        tags=["essays"],
        operation_id="essays_grading_partial_update",
        description="Update grading result for an essay. Not yet implemented.",
        request=None,
        responses={
            **error_responses(401, 501),
        },
    )
    def patch(self, request: AuthenticatedRequest, essay_id: uuid.UUID) -> Response:
        return Response(
            {"detail": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED
        )


class EssayGradingApproveView(APIView):
    """Approve grading result."""

    @extend_schema(
        tags=["essays"],
        operation_id="essays_grading_approve",
        description="Approve an AI grading result. Not yet implemented.",
        request=None,
        responses={
            **error_responses(401, 501),
        },
    )
    def post(self, request: AuthenticatedRequest, essay_id: uuid.UUID) -> Response:
        return Response(
            {"detail": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED
        )
