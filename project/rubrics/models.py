import uuid

from django.conf import settings
from django.db import models


class Rubric(models.Model):
    """A grading rubric owned by a teacher."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rubrics'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class RubricCriterion(models.Model):
    """A criterion within a rubric (e.g., 'Thesis and Argumentation')."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rubric = models.ForeignKey(
        Rubric, on_delete=models.CASCADE, related_name='criteria'
    )
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.rubric.title} - {self.name}"


class CriterionLevel(models.Model):
    """A score level within a criterion (e.g., score of 3 with descriptor)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    criterion = models.ForeignKey(
        RubricCriterion, on_delete=models.CASCADE, related_name='levels'
    )
    score = models.IntegerField()
    descriptor = models.TextField()

    class Meta:
        ordering = ['score']

    def __str__(self):
        return f"{self.criterion.name} - Level {self.score}"
