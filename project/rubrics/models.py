from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from accounts.models import User
from django.db import models

if TYPE_CHECKING:
    from assignments.models import Assignment


class Rubric(models.Model):
    """A grading rubric owned by a teacher."""

    if TYPE_CHECKING:
        criteria: models.Manager[RubricCriterion]
        assignments: models.Manager[Assignment]

    id = models.UUIDField[uuid.UUID | str, uuid.UUID](
        primary_key=True, default=uuid.uuid4, editable=False
    )
    user = models.ForeignKey[User, User](
        User, on_delete=models.CASCADE, related_name="rubrics"
    )
    title = models.CharField[str, str](max_length=255)
    description = models.TextField[str, str](blank=True)
    created_at = models.DateTimeField[datetime | str, datetime](auto_now_add=True)
    updated_at = models.DateTimeField[datetime | str, datetime](auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class RubricCriterion(models.Model):
    """A criterion within a rubric (e.g., 'Thesis and Argumentation')."""

    id = models.UUIDField[uuid.UUID | str, uuid.UUID](
        primary_key=True, default=uuid.uuid4, editable=False
    )
    rubric = models.ForeignKey[Rubric, Rubric](
        Rubric, on_delete=models.CASCADE, related_name="criteria"
    )
    name = models.CharField[str, str](max_length=255)
    order = models.IntegerField[int | str, int](default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.rubric.title} - {self.name}"


class CriterionLevel(models.Model):
    """A score level within a criterion (e.g., score of 3 with descriptor)."""

    id = models.UUIDField[uuid.UUID | str, uuid.UUID](
        primary_key=True, default=uuid.uuid4, editable=False
    )
    criterion = models.ForeignKey[RubricCriterion, RubricCriterion](
        RubricCriterion, on_delete=models.CASCADE, related_name="levels"
    )
    score = models.IntegerField[int | str, int]()
    descriptor = models.TextField[str, str]()

    class Meta:
        ordering = ["score"]

    def __str__(self) -> str:
        return f"{self.criterion.name} - Level {self.score}"
