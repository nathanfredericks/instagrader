import uuid

from django.db.models import Case, IntegerField, Value, When
from drf_spectacular.utils import OpenApiExample, extend_schema, inline_serializer  # type: ignore[reportUnknownVariableType]
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.types import AuthenticatedRequest
from instagrader.schema import DetailResponseSerializer, error_responses

from .models import CriterionLevel, Rubric, RubricCriterion
from .serializers import (
    CriterionLevelSerializer,
    RubricCriterionSerializer,
    RubricListSerializer,
    RubricSerializer,
)


class RubricListCreateView(APIView):
    """List user's rubrics or create a new rubric."""

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_rubric_list",
        description="List all rubrics owned by the authenticated user.",
        responses={
            200: RubricListSerializer(many=True),
            **error_responses(401),
        },
    )
    def get(self, request: AuthenticatedRequest) -> Response:
        rubrics = Rubric.objects.filter(user=request.user)
        serializer = RubricListSerializer(rubrics, many=True)
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_rubric_create",
        description="Create a new rubric.",
        request=RubricSerializer,
        responses={
            201: RubricSerializer,
            **error_responses(400, 401),
        },
    )
    def post(self, request: AuthenticatedRequest) -> Response:
        serializer = RubricSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)  # type: ignore[reportUnknownMemberType]


class RubricDetailView(APIView):
    """Get, update, or delete a rubric."""

    def _get_rubric(
        self, request: AuthenticatedRequest, rubric_id: uuid.UUID
    ) -> Rubric | None:
        try:
            return Rubric.objects.prefetch_related("criteria__levels").get(
                id=rubric_id, user=request.user
            )
        except Rubric.DoesNotExist:
            return None

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_rubric_retrieve",
        description="Retrieve a rubric with nested criteria and levels.",
        responses={
            200: RubricSerializer,
            **error_responses(401, 404),
        },
    )
    def get(self, request: AuthenticatedRequest, rubric_id: uuid.UUID) -> Response:
        rubric = self._get_rubric(request, rubric_id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = RubricSerializer(rubric)
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_rubric_partial_update",
        description="Partially update a rubric's title or description.",
        request=RubricSerializer,
        responses={
            200: RubricSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def patch(self, request: AuthenticatedRequest, rubric_id: uuid.UUID) -> Response:
        rubric = self._get_rubric(request, rubric_id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = RubricSerializer(rubric, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_rubric_delete",
        description="Delete a rubric. Fails if any assignment references it.",
        responses={
            204: None,
            400: DetailResponseSerializer,
            **error_responses(401, 404),
        },
        examples=[
            OpenApiExample(
                "Rubric in use",
                value={"detail": "Cannot delete rubric that is in use by assignments."},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def delete(self, request: AuthenticatedRequest, rubric_id: uuid.UUID) -> Response:
        rubric = self._get_rubric(request, rubric_id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if rubric.assignments.exists():
            return Response(
                {"detail": "Cannot delete rubric that is in use by assignments."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rubric.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CriterionListCreateView(APIView):
    """Add a criterion to a rubric."""

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_criterion_create",
        description="Add a criterion to a rubric.",
        request=RubricCriterionSerializer,
        responses={
            201: RubricCriterionSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def post(self, request: AuthenticatedRequest, rubric_id: uuid.UUID) -> Response:
        try:
            rubric = Rubric.objects.get(id=rubric_id, user=request.user)
        except Rubric.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = RubricCriterionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(rubric=rubric)
        return Response(serializer.data, status=status.HTTP_201_CREATED)  # type: ignore[reportUnknownMemberType]


class CriterionDetailView(APIView):
    """Update or delete a criterion."""

    def _get_criterion(
        self,
        request: AuthenticatedRequest,
        rubric_id: uuid.UUID,
        criterion_id: uuid.UUID,
    ) -> RubricCriterion | None:
        try:
            Rubric.objects.get(id=rubric_id, user=request.user)
        except Rubric.DoesNotExist:
            return None
        try:
            return RubricCriterion.objects.get(id=criterion_id, rubric_id=rubric_id)
        except RubricCriterion.DoesNotExist:
            return None

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_criterion_partial_update",
        description="Partially update a criterion's name or order.",
        request=RubricCriterionSerializer,
        responses={
            200: RubricCriterionSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def patch(
        self,
        request: AuthenticatedRequest,
        rubric_id: uuid.UUID,
        criterion_id: uuid.UUID,
    ) -> Response:
        criterion = self._get_criterion(request, rubric_id, criterion_id)
        if criterion is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = RubricCriterionSerializer(
            criterion, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_criterion_delete",
        description="Delete a criterion and all its levels.",
        responses={
            204: None,
            **error_responses(401, 404),
        },
    )
    def delete(
        self,
        request: AuthenticatedRequest,
        rubric_id: uuid.UUID,
        criterion_id: uuid.UUID,
    ) -> Response:
        criterion = self._get_criterion(request, rubric_id, criterion_id)
        if criterion is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        criterion.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CriterionReorderView(APIView):
    """Reorder criteria within a rubric."""

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_criterion_reorder",
        description="Reorder criteria within a rubric. Provide all criterion UUIDs in desired order.",
        request=inline_serializer(
            name="CriterionReorderRequest",
            fields={
                "order": serializers.ListField(
                    child=serializers.UUIDField(),
                    help_text="List of all criterion UUIDs in the desired order.",
                ),
            },
        ),
        responses={
            200: None,
            400: DetailResponseSerializer,
            **error_responses(401, 404),
        },
        examples=[
            OpenApiExample(
                "Reorder request",
                value={
                    "order": [
                        "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    ]
                },
                request_only=True,
            ),
            OpenApiExample(
                "Empty order list",
                value={"detail": "Order list cannot be empty."},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Duplicate IDs",
                value={"detail": "Duplicate IDs in order list."},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Incomplete order list",
                value={"detail": "Order list must contain exactly all criteria IDs."},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request: AuthenticatedRequest, rubric_id: uuid.UUID) -> Response:
        try:
            rubric = Rubric.objects.get(id=rubric_id, user=request.user)
        except Rubric.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        order = request.data.get("order", [])
        if not order:
            return Response(
                {"detail": "Order list cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(order) != len(set(order)):
            return Response(
                {"detail": "Duplicate IDs in order list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_ids = set(
            str(cid) for cid in rubric.criteria.values_list("id", flat=True)
        )
        provided_ids = set(str(cid) for cid in order)
        if provided_ids != existing_ids:
            return Response(
                {"detail": "Order list must contain exactly all criteria IDs."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        whens = [
            When(id=criterion_id, then=Value(index))
            for index, criterion_id in enumerate(order)
        ]
        RubricCriterion.objects.filter(rubric=rubric).update(
            order=Case(*whens, output_field=IntegerField())
        )

        return Response(status=status.HTTP_200_OK)


class LevelListCreateView(APIView):
    """Add a level to a criterion."""

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_level_create",
        description="Add a scoring level to a criterion.",
        request=CriterionLevelSerializer,
        responses={
            201: CriterionLevelSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def post(
        self,
        request: AuthenticatedRequest,
        rubric_id: uuid.UUID,
        criterion_id: uuid.UUID,
    ) -> Response:
        try:
            rubric = Rubric.objects.get(id=rubric_id, user=request.user)
        except Rubric.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            criterion = RubricCriterion.objects.get(id=criterion_id, rubric=rubric)
        except RubricCriterion.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CriterionLevelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(criterion=criterion)
        return Response(serializer.data, status=status.HTTP_201_CREATED)  # type: ignore[reportUnknownMemberType]


class LevelDetailView(APIView):
    """Update or delete a level."""

    def _get_level(
        self,
        request: AuthenticatedRequest,
        rubric_id: uuid.UUID,
        criterion_id: uuid.UUID,
        level_id: uuid.UUID,
    ) -> CriterionLevel | None:
        try:
            Rubric.objects.get(id=rubric_id, user=request.user)
        except Rubric.DoesNotExist:
            return None
        try:
            RubricCriterion.objects.get(id=criterion_id, rubric_id=rubric_id)
        except RubricCriterion.DoesNotExist:
            return None
        try:
            return CriterionLevel.objects.get(id=level_id, criterion_id=criterion_id)
        except CriterionLevel.DoesNotExist:
            return None

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_level_partial_update",
        description="Partially update a scoring level's score or descriptor.",
        request=CriterionLevelSerializer,
        responses={
            200: CriterionLevelSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def patch(
        self,
        request: AuthenticatedRequest,
        rubric_id: uuid.UUID,
        criterion_id: uuid.UUID,
        level_id: uuid.UUID,
    ) -> Response:
        level = self._get_level(request, rubric_id, criterion_id, level_id)
        if level is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = CriterionLevelSerializer(level, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_level_delete",
        description="Delete a scoring level.",
        responses={
            204: None,
            **error_responses(401, 404),
        },
    )
    def delete(
        self,
        request: AuthenticatedRequest,
        rubric_id: uuid.UUID,
        criterion_id: uuid.UUID,
        level_id: uuid.UUID,
    ) -> Response:
        level = self._get_level(request, rubric_id, criterion_id, level_id)
        if level is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        level.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
