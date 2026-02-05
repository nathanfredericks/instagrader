import uuid

from django.db import models


class GradingResult(models.Model):
    """The overall grading result for an essay."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    essay = models.OneToOneField(
        'assignments.Essay', on_delete=models.CASCADE, related_name='grading_result'
    )
    teacher_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Grading for {self.essay}"


class CriterionScore(models.Model):
    """A score for a single criterion within a grading result."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grading_result = models.ForeignKey(
        GradingResult, on_delete=models.CASCADE, related_name='criterion_scores'
    )
    criterion = models.ForeignKey(
        'rubrics.RubricCriterion', on_delete=models.PROTECT, related_name='scores'
    )
    level = models.ForeignKey(
        'rubrics.CriterionLevel',
        on_delete=models.PROTECT,
        related_name='scores',
        help_text='The level achieved (links to score)',
    )
    feedback = models.TextField(help_text='AI feedback for this criterion')
    teacher_level = models.ForeignKey(
        'rubrics.CriterionLevel',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='teacher_scores',
        help_text='Teacher override level',
    )
    teacher_feedback = models.TextField(
        blank=True, help_text='Teacher override feedback'
    )

    class Meta:
        ordering = ['criterion__order']

    def __str__(self):
        return f"{self.criterion.name} - {self.level.score}"
