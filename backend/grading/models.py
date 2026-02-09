import uuid
from datetime import datetime

from django.db import models

from assignments.models import Essay
from rubrics.models import CriterionLevel, RubricCriterion


class GradingResult(models.Model):
    """The overall grading result for an essay."""

    id = models.UUIDField[uuid.UUID | str, uuid.UUID](
        primary_key=True, default=uuid.uuid4, editable=False
    )
    essay = models.OneToOneField[Essay, Essay](
        Essay, on_delete=models.CASCADE, related_name="grading_result"
    )
    teacher_approved = models.BooleanField[bool | str, bool](default=False)
    approved_at = models.DateTimeField[datetime | str | None, datetime | None](
        null=True, blank=True
    )
    created_at = models.DateTimeField[datetime | str, datetime](auto_now_add=True)
    updated_at = models.DateTimeField[datetime | str, datetime](auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Grading for {self.essay}"


class CriterionScore(models.Model):
    """A score for a single criterion within a grading result."""

    id = models.UUIDField[uuid.UUID | str, uuid.UUID](
        primary_key=True, default=uuid.uuid4, editable=False
    )
    grading_result = models.ForeignKey[GradingResult, GradingResult](
        GradingResult, on_delete=models.CASCADE, related_name="criterion_scores"
    )
    criterion = models.ForeignKey[RubricCriterion, RubricCriterion](
        RubricCriterion, on_delete=models.PROTECT, related_name="scores"
    )
    level = models.ForeignKey[CriterionLevel, CriterionLevel](
        CriterionLevel,
        on_delete=models.PROTECT,
        related_name="scores",
        help_text="The level achieved (links to score)",
    )
    feedback = models.TextField[str, str](help_text="AI feedback for this criterion")
    teacher_level = models.ForeignKey[CriterionLevel | None, CriterionLevel | None](
        CriterionLevel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="teacher_scores",
        help_text="Teacher override level",
    )
    teacher_feedback = models.TextField[str, str](
        blank=True, help_text="Teacher override feedback"
    )

    class Meta:
        ordering = ["criterion__order"]

    def __str__(self) -> str:
        return f"{self.criterion.name} - {self.level.score}"
