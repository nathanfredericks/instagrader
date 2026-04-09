from django.db.models import Count, Q
from drf_spectacular.utils import (  # type: ignore[reportUnknownVariableType]
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.types import AuthenticatedRequest
from assignments.models import Assignment, Essay
from grading.models import GradingResult
from instagrader.schema import error_responses

ACTIVITY_LIMIT = 10
ACTIVE_ASSIGNMENTS_LIMIT = 3
SCORE_RANGES = [
    ("0-20", 0, 20),
    ("21-40", 21, 40),
    ("41-60", 41, 60),
    ("61-80", 61, 80),
    ("81-100", 81, 100),
]


class DashboardView(APIView):
    """Aggregated dashboard statistics for the authenticated user."""

    @extend_schema(
        tags=["dashboard"],
        operation_id="dashboard_stats",
        description="Get aggregated grading statistics for the authenticated user.",
        responses={
            200: inline_serializer(  # type: ignore[reportUnknownVariableType]
                name="DashboardResponse",
                fields={
                    "essay_status_counts": inline_serializer(  # type: ignore[reportUnknownVariableType]
                        name="EssayStatusCounts",
                        fields={
                            "pending": serializers.IntegerField(),
                            "processing": serializers.IntegerField(),
                            "graded": serializers.IntegerField(),
                            "reviewed": serializers.IntegerField(),
                            "failed": serializers.IntegerField(),
                        },
                    ),
                    "assignment_status_counts": inline_serializer(  # type: ignore[reportUnknownVariableType]
                        name="AssignmentStatusCounts",
                        fields={
                            "draft": serializers.IntegerField(),
                            "grading": serializers.IntegerField(),
                            "review": serializers.IntegerField(),
                            "completed": serializers.IntegerField(),
                        },
                    ),
                    "recent_activity": serializers.ListField(
                        child=inline_serializer(  # type: ignore[reportUnknownVariableType]
                            name="RecentActivityItem",
                            fields={
                                "type": serializers.CharField(),
                                "assignment_title": serializers.CharField(),
                                "assignment_id": serializers.UUIDField(),
                                "essay_id": serializers.UUIDField(allow_null=True),
                                "essay_file_name": serializers.CharField(
                                    allow_null=True
                                ),
                                "timestamp": serializers.DateTimeField(),
                            },
                        ),
                    ),
                    "totals": inline_serializer(  # type: ignore[reportUnknownVariableType]
                        name="DashboardTotals",
                        fields={
                            "total_assignments": serializers.IntegerField(),
                            "total_essays": serializers.IntegerField(),
                        },
                    ),
                    "score_distribution": serializers.ListField(
                        child=inline_serializer(  # type: ignore[reportUnknownVariableType]
                            name="ScoreDistributionBucket",
                            fields={
                                "range": serializers.CharField(),
                                "count": serializers.IntegerField(),
                            },
                        ),
                    ),
                    "active_assignments": serializers.ListField(
                        child=inline_serializer(  # type: ignore[reportUnknownVariableType]
                            name="ActiveAssignment",
                            fields={
                                "id": serializers.UUIDField(),
                                "title": serializers.CharField(),
                                "status": serializers.CharField(),
                                "total_essays": serializers.IntegerField(),
                                "reviewed_count": serializers.IntegerField(),
                                "graded_count": serializers.IntegerField(),
                                "failed_count": serializers.IntegerField(),
                            },
                        ),
                    ),
                },
            ),
            **error_responses(401),
        },
    )
    def get(self, request: AuthenticatedRequest) -> Response:
        user = request.user
        user_essays = Essay.objects.filter(assignment__user=user)
        user_assignments = Assignment.objects.filter(user=user)

        # Essay status counts
        essay_counts_qs = user_essays.values("status").annotate(count=Count("id"))
        essay_status_counts = {s: 0 for s in Essay.Status.values}
        for row in essay_counts_qs:
            essay_status_counts[row["status"]] = row["count"]

        # Assignment status counts
        assignment_counts_qs = user_assignments.values("status").annotate(
            count=Count("id")
        )
        assignment_status_counts = {s: 0 for s in Assignment.Status.values}
        for row in assignment_counts_qs:
            assignment_status_counts[row["status"]] = row["count"]

        # merges 4 separate querysets (created, graded, reviewed, failed) into one timeline sorted by date
        recent_graded = (
            user_essays.filter(status=Essay.Status.GRADED)
            .select_related("assignment")
            .order_by("-updated_at")[:ACTIVITY_LIMIT]
        )

        recent_reviewed = (
            GradingResult.objects.filter(
                essay__assignment__user=user, teacher_approved=True
            )
            .select_related("essay__assignment")
            .order_by("-approved_at")[:ACTIVITY_LIMIT]
        )

        recent_completed = user_assignments.filter(
            status=Assignment.Status.COMPLETED
        ).order_by("-updated_at")[:ACTIVITY_LIMIT]

        recent_failed = (
            user_essays.filter(status=Essay.Status.FAILED)
            .select_related("assignment")
            .order_by("-updated_at")[:ACTIVITY_LIMIT]
        )

        # Normalize into activity items with a common shape
        activity_items = []

        for essay in recent_graded:
            activity_items.append(
                {
                    "type": "essay_graded",
                    "assignment_title": essay.assignment.title,
                    "assignment_id": essay.assignment.id,
                    "essay_id": essay.id,
                    "essay_file_name": essay.file_name,
                    "timestamp": essay.updated_at,
                }
            )

        for result in recent_reviewed:
            activity_items.append(
                {
                    "type": "essay_reviewed",
                    "assignment_title": result.essay.assignment.title,
                    "assignment_id": result.essay.assignment.id,
                    "essay_id": result.essay.id,
                    "essay_file_name": result.essay.file_name,
                    "timestamp": result.approved_at,
                }
            )

        for assignment in recent_completed:
            activity_items.append(
                {
                    "type": "assignment_completed",
                    "assignment_title": assignment.title,
                    "assignment_id": assignment.id,
                    "essay_id": None,
                    "essay_file_name": None,
                    "timestamp": assignment.updated_at,
                }
            )

        for essay in recent_failed:
            activity_items.append(
                {
                    "type": "essay_failed",
                    "assignment_title": essay.assignment.title,
                    "assignment_id": essay.assignment.id,
                    "essay_id": essay.id,
                    "essay_file_name": essay.file_name,
                    "timestamp": essay.updated_at,
                }
            )

        # Sort by timestamp descending, take top N
        activity_items.sort(key=lambda x: x["timestamp"], reverse=True)
        activity_items = activity_items[:ACTIVITY_LIMIT]

        # Totals
        totals = {
            "total_assignments": user_assignments.count(),
            "total_essays": user_essays.count(),
        }

        # calculates percentage of max possible score per criterion, then buckets into ranges
        score_distribution = [
            {"range": label, "count": 0} for label, _, _ in SCORE_RANGES
        ]
        graded_essays = (
            user_essays.filter(
                status__in=[Essay.Status.GRADED, Essay.Status.REVIEWED],
                grading_result__isnull=False,
            )
            .select_related("grading_result")
            .prefetch_related(
                "grading_result__criterion_scores__level",
                "grading_result__criterion_scores__teacher_level",
                "grading_result__criterion_scores__criterion__levels",
            )
        )
        for essay in graded_essays:
            total_score = 0
            max_score = 0
            for cs in essay.grading_result.criterion_scores.all():
                effective_level = cs.teacher_level or cs.level
                total_score += effective_level.score
                max_level = max(
                    (lvl.score for lvl in cs.criterion.levels.all()),
                    default=0,
                )
                max_score += max_level
            if max_score > 0:
                pct = round(total_score / max_score * 100)
                for i, (_, low, high) in enumerate(SCORE_RANGES):
                    if low <= pct <= high:
                        score_distribution[i]["count"] += 1
                        break

        # uses Count with filter=Q() for conditional aggregation in a single query
        active_assignments_qs = (
            user_assignments.filter(
                status__in=[
                    Assignment.Status.GRADING,
                    Assignment.Status.REVIEW,
                ]
            )
            .annotate(
                total_essays=Count("essays"),
                reviewed_count=Count(
                    "essays", filter=Q(essays__status=Essay.Status.REVIEWED)
                ),
                graded_count=Count(
                    "essays", filter=Q(essays__status=Essay.Status.GRADED)
                ),
                failed_count=Count(
                    "essays", filter=Q(essays__status=Essay.Status.FAILED)
                ),
            )
            .order_by("-created_at")[:ACTIVE_ASSIGNMENTS_LIMIT]
        )
        active_assignments = [
            {
                "id": a.id,
                "title": a.title,
                "status": a.status,
                "total_essays": a.total_essays,
                "reviewed_count": a.reviewed_count,
                "graded_count": a.graded_count,
                "failed_count": a.failed_count,
            }
            for a in active_assignments_qs
        ]

        return Response(
            {
                "essay_status_counts": essay_status_counts,
                "assignment_status_counts": assignment_status_counts,
                "recent_activity": activity_items,
                "totals": totals,
                "score_distribution": score_distribution,
                "active_assignments": active_assignments,
            },
            status=status.HTTP_200_OK,
        )
