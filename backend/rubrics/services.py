from datetime import datetime
from typing import Any

from django.db import transaction

from accounts.models import User

from .models import CriterionLevel, Rubric, RubricCriterion
from .templates import TemplateDefinition


class RubricInUseError(Exception):
    """Raised when an operation tries to mutate a rubric in use by assignments."""


class StaleRubricError(Exception):
    """Raised when structure save was based on a stale rubric timestamp."""


def build_conflict_payload(
    detail: str, code: str, suggested_action: str
) -> dict[str, str]:
    return {
        "detail": detail,
        "code": code,
        "suggested_action": suggested_action,
    }


def rubric_is_in_use(rubric: Rubric) -> bool:
    return rubric.assignments.filter(essays__status__in=["graded", "reviewed"]).exists()


def assert_rubric_mutable(rubric: Rubric) -> None:
    if rubric_is_in_use(rubric):
        raise RubricInUseError


def _to_epoch_millis(value: datetime) -> int:
    return int(value.timestamp() * 1000)


# select_for_update locks the row, compares updated_at as epoch millis for stale detection
def save_rubric_structure(rubric: Rubric, payload: dict[str, Any]) -> Rubric:
    """Apply full rubric structure update transactionally."""
    base_updated_at = payload["base_updated_at"]
    name = payload["name"]
    description = payload.get("description", "")
    criteria_payload = payload["criteria"]

    with transaction.atomic():
        locked_rubric = (
            Rubric.objects.select_for_update()
            .prefetch_related("criteria__levels")
            .get(id=rubric.id, user=rubric.user)
        )

        assert_rubric_mutable(locked_rubric)

        if _to_epoch_millis(locked_rubric.updated_at) != _to_epoch_millis(
            base_updated_at
        ):
            raise StaleRubricError

        locked_rubric.name = name
        locked_rubric.description = description
        locked_rubric.save()

        existing_criteria = {str(c.id): c for c in locked_rubric.criteria.all()}
        seen_criteria_ids: set[str] = set()

        # updates existing criteria/levels, creates new ones (id=None), deletes orphans not in the payload
        for criterion_data in criteria_payload:
            criterion_id = str(criterion_data.get("id", "")).strip()
            if criterion_id:
                criterion = existing_criteria.get(criterion_id)
                if criterion is None:
                    raise ValueError(
                        f"Unknown criterion id for this rubric: {criterion_id}"
                    )
                seen_criteria_ids.add(criterion_id)
                criterion.name = criterion_data["name"]
                criterion.order = criterion_data["order"]
                criterion.save()
            else:
                criterion = RubricCriterion.objects.create(
                    rubric=locked_rubric,
                    name=criterion_data["name"],
                    order=criterion_data["order"],
                )

            existing_levels = {str(lv.id): lv for lv in criterion.levels.all()}
            seen_level_ids: set[str] = set()

            for level_data in criterion_data["levels"]:
                level_id = str(level_data.get("id", "")).strip()
                if level_id:
                    level = existing_levels.get(level_id)
                    if level is None:
                        raise ValueError(
                            f"Unknown level id for criterion {criterion.id}: {level_id}"
                        )
                    seen_level_ids.add(level_id)
                    level.order = level_data["order"]
                    level.score = level_data["score"]
                    level.descriptor = level_data["descriptor"]
                    level.save()
                else:
                    CriterionLevel.objects.create(
                        criterion=criterion,
                        order=level_data["order"],
                        score=level_data["score"],
                        descriptor=level_data["descriptor"],
                    )

            for existing_level in criterion.levels.all():
                if str(existing_level.id) not in seen_level_ids:
                    existing_level.delete()

        for existing_criterion in locked_rubric.criteria.all():
            if str(existing_criterion.id) not in seen_criteria_ids:
                existing_criterion.delete()

        refreshed = (
            Rubric.objects.filter(id=locked_rubric.id)
            .prefetch_related("criteria__levels")
            .first()
        )
        if refreshed is None:
            raise ValueError("Rubric not found after structure update.")
        return refreshed


# atomic copy so partial clones dont get persisted
def duplicate_rubric(rubric: Rubric, name: str | None = None) -> Rubric:
    with transaction.atomic():
        cloned = Rubric.objects.create(
            user=rubric.user,
            name=name if name is not None else rubric.name,
            description=rubric.description,
        )

        criteria = rubric.criteria.prefetch_related("levels").all()
        for criterion in criteria:
            cloned_criterion = RubricCriterion.objects.create(
                rubric=cloned,
                name=criterion.name,
                order=criterion.order,
            )
            for level in criterion.levels.all():
                CriterionLevel.objects.create(
                    criterion=cloned_criterion,
                    order=level.order,
                    score=level.score,
                    descriptor=level.descriptor,
                )

        return cloned


# falls back to template name/description if caller doesnt provide overrides
def instantiate_template(
    *,
    user: User,
    template: TemplateDefinition,
    name: str | None,
    description: str | None,
) -> Rubric:
    rubric = Rubric.objects.create(
        user=user,
        name=name if name else str(template["name"]),
        description=description
        if description is not None
        else str(template["description"]),
    )

    criteria = template["criteria"]
    for criterion_index, criterion_data in enumerate(criteria):
        criterion = RubricCriterion.objects.create(
            rubric=rubric,
            name=str(criterion_data["name"]),
            order=criterion_index,
        )
        levels = criterion_data["levels"]
        for level_index, level_data in enumerate(levels):
            CriterionLevel.objects.create(
                criterion=criterion,
                order=level_index,
                score=int(level_data["score"]),
                descriptor=str(level_data["descriptor"]),
            )

    return rubric
