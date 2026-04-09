import uuid
from typing import Any

from django.db.models import Case, IntegerField, Value, When
from drf_spectacular.utils import (
    OpenApiExample,
    extend_schema,  # type: ignore[reportUnknownVariableType]
    inline_serializer,  # type: ignore[reportUnknownVariableType]
)
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.types import AuthenticatedRequest
from instagrader.schema import DetailResponseSerializer, error_responses

from .models import CriterionLevel, Rubric, RubricCriterion
from .serializers import (
    CriterionLevelSerializer,
    RubricCriterionSerializer,
    RubricDuplicateSerializer,
    RubricListSerializer,
    RubricSerializer,
    RubricStructureSerializer,
    RubricTemplateInstantiateSerializer,
    RubricTemplateSummarySerializer,
)
from .services import (
    RubricInUseError,
    StaleRubricError,
    assert_rubric_mutable,
    build_conflict_payload,
    duplicate_rubric,
    instantiate_template,
    save_rubric_structure,
)
from .templates import RUBRIC_TEMPLATES, build_template_summary, get_template_by_key

ConflictResponseSerializer = inline_serializer(  # type: ignore[reportUnknownVariableType]
    name="RubricConflictResponse",
    fields={
        "detail": serializers.CharField(),
        "code": serializers.CharField(),
        "suggested_action": serializers.CharField(),
    },
)


def in_use_conflict_payload() -> dict[str, str]:
    return build_conflict_payload(
        detail=(
            "This rubric cannot be edited because one or more linked essays are "
            "graded or reviewed."
        ),
        code="rubric_in_use",
        suggested_action="duplicate_rubric",
    )


def stale_conflict_payload() -> dict[str, str]:
    return build_conflict_payload(
        detail="This rubric was updated elsewhere. Reload and try saving again.",
        code="stale_structure_version",
        suggested_action="reload_rubric",
    )


def conflict_response(payload: dict[str, str]) -> Response:
    return Response(payload, status=status.HTTP_409_CONFLICT)


def owned_rubrics(request: AuthenticatedRequest):
    return Rubric.objects.filter(user=request.user)


# prefetch_related prevents n+1 queries on criteria and levels
def fetch_owned_rubric(
    request: AuthenticatedRequest, rubric_id: uuid.UUID
) -> Rubric | None:
    return (
        owned_rubrics(request)
        .prefetch_related("criteria__levels")
        .filter(id=rubric_id)
        .first()
    )


class RubricTemplateListView(APIView):
    """List available rubric templates."""

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_template_list",
        description="List built-in rubric templates.",
        responses={
            200: RubricTemplateSummarySerializer(many=True),
            **error_responses(401),
        },
    )
    def get(self, _request: AuthenticatedRequest) -> Response:
        summaries = [build_template_summary(template) for template in RUBRIC_TEMPLATES]
        serializer = RubricTemplateSummarySerializer(summaries, many=True)
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]


class RubricTemplateInstantiateView(APIView):
    """Instantiate a rubric from a template."""

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_template_instantiate",
        description="Create a rubric from the selected template.",
        request=RubricTemplateInstantiateSerializer,
        responses={201: RubricSerializer, **error_responses(400, 401, 404)},
    )
    def post(self, request: AuthenticatedRequest, template_key: str) -> Response:
        template = get_template_by_key(template_key)
        if template is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = RubricTemplateInstantiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        rubric = instantiate_template(
            user=request.user,
            template=template,
            name=data.get("name"),
            description=data.get("description"),
        )
        rubric = fetch_owned_rubric(request, rubric.id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(RubricSerializer(rubric).data, status=status.HTTP_201_CREATED)  # type: ignore[reportUnknownMemberType]


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
        rubrics = owned_rubrics(request).order_by("-updated_at", "-created_at")
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
        rubric = serializer.save(user=request.user)
        rubric = fetch_owned_rubric(request, rubric.id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(RubricSerializer(rubric).data, status=status.HTTP_201_CREATED)  # type: ignore[reportUnknownMemberType]


class RubricDetailView(APIView):
    """Get, update, or delete a rubric."""

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
        rubric = fetch_owned_rubric(request, rubric_id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = RubricSerializer(rubric)
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_rubric_partial_update",
        description="Partially update a rubric's name or description.",
        request=RubricSerializer,
        responses={
            200: RubricSerializer,
            409: ConflictResponseSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def patch(self, request: AuthenticatedRequest, rubric_id: uuid.UUID) -> Response:
        rubric = fetch_owned_rubric(request, rubric_id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            assert_rubric_mutable(rubric)
        except RubricInUseError:
            return conflict_response(in_use_conflict_payload())

        serializer = RubricSerializer(rubric, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        refreshed = fetch_owned_rubric(request, rubric_id)
        if refreshed is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(RubricSerializer(refreshed).data)  # type: ignore[reportUnknownMemberType]

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
        rubric = fetch_owned_rubric(request, rubric_id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if rubric.assignments.exists():
            return Response(
                {"detail": "Cannot delete rubric that is in use by assignments."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rubric.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RubricDuplicateView(APIView):
    """Clone an existing rubric into a new rubric."""

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_rubric_duplicate",
        description="Duplicate a rubric by cloning it into a new editable rubric.",
        request=RubricDuplicateSerializer,
        responses={201: RubricSerializer, **error_responses(400, 401, 404)},
    )
    def post(self, request: AuthenticatedRequest, rubric_id: uuid.UUID) -> Response:
        rubric = fetch_owned_rubric(request, rubric_id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = RubricDuplicateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data.get("name")

        cloned = duplicate_rubric(rubric, name=name)
        cloned = fetch_owned_rubric(request, cloned.id)
        if cloned is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(RubricSerializer(cloned).data, status=status.HTTP_201_CREATED)  # type: ignore[reportUnknownMemberType]


class RubricStructureView(APIView):
    """Apply a complete rubric structure update atomically."""

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_rubric_structure_update",
        description=(
            "Replace a rubric's full structure (name, criteria, levels) atomically."
        ),
        request=RubricStructureSerializer,
        responses={
            200: RubricSerializer,
            409: ConflictResponseSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def put(self, request: AuthenticatedRequest, rubric_id: uuid.UUID) -> Response:
        rubric = fetch_owned_rubric(request, rubric_id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = RubricStructureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = save_rubric_structure(rubric, serializer.validated_data)
        # catches StaleRubricError for optimistic locking, RubricInUseError if rubric is attached to an assignment
        except RubricInUseError:
            return conflict_response(in_use_conflict_payload())
        except StaleRubricError:
            return conflict_response(stale_conflict_payload())
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        refreshed = fetch_owned_rubric(request, updated.id)
        if refreshed is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(RubricSerializer(refreshed).data)  # type: ignore[reportUnknownMemberType]


class CriterionListCreateView(APIView):
    """Add a criterion to a rubric."""

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_criterion_create",
        description="Add a criterion to a rubric.",
        request=RubricCriterionSerializer,
        responses={
            201: RubricCriterionSerializer,
            409: ConflictResponseSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def post(self, request: AuthenticatedRequest, rubric_id: uuid.UUID) -> Response:
        rubric = fetch_owned_rubric(request, rubric_id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            assert_rubric_mutable(rubric)
        except RubricInUseError:
            return conflict_response(in_use_conflict_payload())

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
        rubric = fetch_owned_rubric(request, rubric_id)
        if rubric is None:
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
            409: ConflictResponseSerializer,
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

        try:
            assert_rubric_mutable(criterion.rubric)
        except RubricInUseError:
            return conflict_response(in_use_conflict_payload())

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
            409: ConflictResponseSerializer,
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

        try:
            assert_rubric_mutable(criterion.rubric)
        except RubricInUseError:
            return conflict_response(in_use_conflict_payload())

        criterion.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CriterionReorderView(APIView):
    """Reorder criteria within a rubric."""

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_criterion_reorder",
        description=(
            "Reorder criteria within a rubric."
            " Provide all criterion UUIDs in desired order."
        ),
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
            409: ConflictResponseSerializer,
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
                "Incomplete order list",
                value={"detail": "Order list must contain exactly all criteria IDs."},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    def post(self, request: AuthenticatedRequest, rubric_id: uuid.UUID) -> Response:
        rubric = fetch_owned_rubric(request, rubric_id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            assert_rubric_mutable(rubric)
        except RubricInUseError:
            return conflict_response(in_use_conflict_payload())

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

        # uses Case/When to update all criterion positions in a single query
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
            409: ConflictResponseSerializer,
            **error_responses(400, 401, 404),
        },
    )
    def post(
        self,
        request: AuthenticatedRequest,
        rubric_id: uuid.UUID,
        criterion_id: uuid.UUID,
    ) -> Response:
        rubric = fetch_owned_rubric(request, rubric_id)
        if rubric is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            assert_rubric_mutable(rubric)
        except RubricInUseError:
            return conflict_response(in_use_conflict_payload())

        try:
            criterion = RubricCriterion.objects.get(id=criterion_id, rubric=rubric)
        except RubricCriterion.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        payload: dict[str, Any] = request.data.copy()
        if "order" not in payload:
            payload["order"] = criterion.levels.count()

        serializer = CriterionLevelSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        score = int(serializer.validated_data["score"])
        if criterion.levels.filter(score=score).exists():
            return Response(
                {"detail": "Level scores must be unique within each criterion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
        rubric = fetch_owned_rubric(request, rubric_id)
        if rubric is None:
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
            409: ConflictResponseSerializer,
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

        try:
            assert_rubric_mutable(level.criterion.rubric)
        except RubricInUseError:
            return conflict_response(in_use_conflict_payload())

        serializer = CriterionLevelSerializer(level, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        new_score = serializer.validated_data.get("score")
        if (
            new_score is not None
            and level.criterion.levels.exclude(id=level.id)
            .filter(score=int(new_score))
            .exists()
        ):
            return Response(
                {"detail": "Level scores must be unique within each criterion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        return Response(serializer.data)  # type: ignore[reportUnknownMemberType]

    @extend_schema(
        tags=["rubrics"],
        operation_id="rubrics_level_delete",
        description="Delete a scoring level.",
        responses={
            204: None,
            409: ConflictResponseSerializer,
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

        try:
            assert_rubric_mutable(level.criterion.rubric)
        except RubricInUseError:
            return conflict_response(in_use_conflict_payload())

        level.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
