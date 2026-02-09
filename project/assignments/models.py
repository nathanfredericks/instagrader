from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from accounts.models import User
from django.db import models
from rubrics.models import Rubric


class Assignment(models.Model):
    """An assignment created by a teacher."""

    if TYPE_CHECKING:
        essays: models.Manager[Essay]

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        GRADING = "grading", "Grading"
        REVIEW = "review", "Review"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField[uuid.UUID | str, uuid.UUID](
        primary_key=True, default=uuid.uuid4, editable=False
    )
    user = models.ForeignKey[User, User](
        User, on_delete=models.CASCADE, related_name="assignments"
    )
    rubric = models.ForeignKey[Rubric, Rubric](
        Rubric, on_delete=models.PROTECT, related_name="assignments"
    )
    title = models.CharField[str, str](max_length=255)
    prompt = models.TextField[str, str](help_text="Writing assignment prompt for AI")
    source_text = models.TextField[str, str](
        blank=True, help_text="Reference material for the essay"
    )
    status = models.CharField[str, str](
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    created_at = models.DateTimeField[datetime | str, datetime](auto_now_add=True)
    updated_at = models.DateTimeField[datetime | str, datetime](auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Essay(models.Model):
    """A student essay submission."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        GRADED = "graded", "Graded"
        REVIEWED = "reviewed", "Reviewed"
        FAILED = "failed", "Failed"

    id = models.UUIDField[uuid.UUID | str, uuid.UUID](
        primary_key=True, default=uuid.uuid4, editable=False
    )
    assignment = models.ForeignKey[Assignment, Assignment](
        Assignment, on_delete=models.CASCADE, related_name="essays"
    )
    file_name = models.CharField[str, str](
        max_length=255, help_text="Original filename of the uploaded essay"
    )
    original_file = models.FileField(upload_to="essays/")
    extracted_text = models.TextField[str, str](
        blank=True, help_text="Converted text (via MarkItDown later)"
    )
    status = models.CharField[str, str](
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField[datetime | str, datetime](auto_now_add=True)
    updated_at = models.DateTimeField[datetime | str, datetime](auto_now=True)

    class Meta:
        ordering = ["file_name"]

    def __str__(self) -> str:
        return f"{self.file_name} - {self.assignment.title}"
