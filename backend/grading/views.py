import uuid

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import (
    extend_schema,  # type: ignore[reportUnknownVariableType]
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.types import AuthenticatedRequest
from assignments.models import Essay
from assignments.serializers import EssayListSerializer, EssaySerializer
from instagrader.schema import error_responses

from .models import CriterionScore, GradingResult
from .serializers import (
    GradingResultApproveSerializer,
    GradingResultSerializer,
)


def _apply_criterion_score_updates(
    *,
    grading_result: GradingResult,
    score_updates: list[dict],
) -> Response | None:
    """Apply teacher updates to criterion scores with consistency validation."""
    for score_data in score_updates:
        try:
            criterion_score = CriterionScore.objects.get(
                id=score_data["id"], grading_result=grading_result
            )
        except CriterionScore.DoesNotExist:
            return Response(
                {"detail": f"Criterion score {score_data['id']} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        review_state = score_data.get("teacher_review_state")
        teacher_level = score_data.get("teacher_level", criterion_score.teacher_level)

        # backward compat, old clients send teacher_level without review_state so we infer it
        if review_state is None and "teacher_level" in score_data:
            review_state = (
                CriterionScore.ReviewState.OVERRIDDEN
                if score_data["teacher_level"] is not None
                else CriterionScore.ReviewState.ACCEPTED_AI
            )

        if review_state is None:
            review_state = criterion_score.teacher_review_state

        if (
            review_state == CriterionScore.ReviewState.OVERRIDDEN
            and teacher_level is None
        ):
            return Response(
                {
                    "detail": (
                        "teacher_level is required when "
                        "teacher_review_state is 'overridden'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            review_state == CriterionScore.ReviewState.ACCEPTED_AI
            and "teacher_level" in score_data
            and score_data["teacher_level"] is not None
        ):
            return Response(
                {
                    "detail": (
                        "teacher_level must be null when "
                        "teacher_review_state is 'accepted_ai'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "teacher_level" in score_data:
            criterion_score.teacher_level = score_data["teacher_level"]
        if "teacher_feedback" in score_data:
            criterion_score.teacher_feedback = score_data["teacher_feedback"]

        criterion_score.teacher_review_state = review_state
        if review_state == CriterionScore.ReviewState.PENDING:
            criterion_score.teacher_reviewed_at = None
        else:
            criterion_score.teacher_reviewed_at = timezone.now()

        # clears teacher_level for non-overridden states, effective score always comes from ai
        if review_state != CriterionScore.ReviewState.OVERRIDDEN:
            criterion_score.teacher_level = None

        criterion_score.save(
            update_fields=[
                "teacher_level",
                "teacher_feedback",
                "teacher_review_state",
                "teacher_reviewed_at",
            ]
        )

    return None


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
        description="Get grading result for an essay.",
        responses={
            200: GradingResultSerializer,
            **error_responses(401, 404),
        },
    )
    def get(self, request: AuthenticatedRequest, essay_id: uuid.UUID) -> Response:
        try:
            essay = Essay.objects.get(id=essay_id, assignment__user=request.user)
        except Essay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            grading_result = GradingResult.objects.prefetch_related(
                "criterion_scores"
            ).get(essay=essay)
        except GradingResult.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = GradingResultSerializer(grading_result)
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]

    @extend_schema(
        tags=["essays"],
        operation_id="essays_grading_save",
        description=(
            "Save teacher criterion score updates without approving the grading result."
        ),
        request=GradingResultApproveSerializer,
        responses={
            200: GradingResultSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def patch(self, request: AuthenticatedRequest, essay_id: uuid.UUID) -> Response:
        try:
            essay = Essay.objects.get(id=essay_id, assignment__user=request.user)
        except Essay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            grading_result = GradingResult.objects.prefetch_related(
                "criterion_scores"
            ).get(essay=essay)
        except GradingResult.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        save_serializer = GradingResultApproveSerializer(data=request.data or {})
        save_serializer.is_valid(raise_exception=True)

        score_updates = save_serializer.validated_data.get("criterion_scores", [])
        if score_updates:
            error_response = _apply_criterion_score_updates(
                grading_result=grading_result,
                score_updates=score_updates,
            )
            if error_response is not None:
                return error_response

        serializer = GradingResultSerializer(grading_result)
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]


class EssayGradingApproveView(APIView):
    """Approve grading result."""

    @extend_schema(
        tags=["essays"],
        operation_id="essays_grading_approve",
        description=(
            "Approve an AI grading result, transitioning the essay to REVIEWED."
        ),
        request=GradingResultApproveSerializer,
        responses={
            200: GradingResultSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def post(self, request: AuthenticatedRequest, essay_id: uuid.UUID) -> Response:
        try:
            essay = Essay.objects.select_related("assignment").get(
                id=essay_id, assignment__user=request.user
            )
        except Essay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            grading_result = GradingResult.objects.get(essay=essay)
        except GradingResult.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # atomic transaction, rolls back if any criteria still pending
        with transaction.atomic():
            if grading_result.teacher_approved:
                return Response(
                    {"detail": "Grading result already approved."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            approve_serializer = GradingResultApproveSerializer(data=request.data or {})
            approve_serializer.is_valid(raise_exception=True)

            score_updates = approve_serializer.validated_data.get(
                "criterion_scores", []
            )
            if score_updates:
                error_response = _apply_criterion_score_updates(
                    grading_result=grading_result,
                    score_updates=score_updates,
                )
                if error_response is not None:
                    transaction.set_rollback(True)
                    return error_response

            has_pending_criteria = grading_result.criterion_scores.filter(
                teacher_review_state=CriterionScore.ReviewState.PENDING
            ).exists()
            if has_pending_criteria:
                transaction.set_rollback(True)
                return Response(
                    {
                        "detail": (
                            "All criterion_scores must be reviewed before approval."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            grading_result.teacher_approved = True
            grading_result.approved_at = timezone.now()
            grading_result.save(update_fields=["teacher_approved", "approved_at"])

            essay.status = Essay.Status.REVIEWED
            essay.save(update_fields=["status"])

            # triggers assignment state transition review -> completed if all essays reviewed
            essay.assignment.check_review_complete()

        serializer = GradingResultSerializer(grading_result)
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]


class EssayRetryView(APIView):
    """Retry processing/grading for an essay."""

    @extend_schema(
        tags=["essays"],
        operation_id="essays_retry",
        description=(
            "Retry processing/grading for an essay by moving it back "
            "to PENDING and re-queuing the batch pipeline."
        ),
        request=None,
        responses={
            200: EssayListSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def post(self, request: AuthenticatedRequest, essay_id: uuid.UUID) -> Response:
        from assignments.models import Assignment
        from assignments.tasks import process_essay_batch
        from grading.models import GradingResult

        try:
            essay = Essay.objects.select_related("assignment").get(
                id=essay_id, assignment__user=request.user
            )
        except Essay.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if essay.status in (Essay.Status.PENDING, Essay.Status.PROCESSING):
            return Response(
                {
                    "detail": (
                        "Cannot retry an essay that is already pending or processing."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # deletes stale grading result from prior run before requeueing
        GradingResult.objects.filter(essay=essay).delete()

        essay.status = Essay.Status.PENDING
        essay.extracted_text = ""
        essay.failure_reason = ""
        essay.save(update_fields=["status", "extracted_text", "failure_reason"])

        assignment = essay.assignment
        result = process_essay_batch.delay([str(essay.id)])
        assignment.celery_task_id = str(result.id)
        if assignment.status != Assignment.Status.GRADING:
            assignment.status = Assignment.Status.GRADING
            assignment.save(update_fields=["status", "celery_task_id"])
        else:
            assignment.save(update_fields=["celery_task_id"])
        assignment.start_grading_timer_if_needed()

        serializer = EssayListSerializer(essay)
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]
