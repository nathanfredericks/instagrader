import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

from accounts.models import User
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
    title = models.CharField[str, str](max_length=255)  # rename to name
    description = models.TextField[str, str](blank=True, default="")  # add help text
    prompt = models.TextField[str, str](help_text="Writing assignment prompt for AI")
    source_text = models.TextField[str, str](
        blank=True, help_text="Reference material for the essay"
    )
    status = models.CharField[str, str](
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    celery_task_id = models.CharField[str, str](
        max_length=255, blank=True, help_text="Active Celery task ID for grading"
    )
    grading_started_at = models.DateTimeField[datetime | str, datetime](
        null=True,
        blank=True,
        help_text="When the current grading run started",
    )
    grading_completed_at = models.DateTimeField[datetime | str, datetime](
        null=True,
        blank=True,
        help_text="When the last grading run finished",
    )
    created_at = models.DateTimeField[datetime | str, datetime](auto_now_add=True)
    updated_at = models.DateTimeField[datetime | str, datetime](auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def start_grading_timer_if_needed(self) -> None:
        if self.grading_started_at is not None:
            return
        self.grading_started_at = timezone.now()
        self.grading_completed_at = None
        self.save(update_fields=["grading_started_at", "grading_completed_at"])

    def reset_grading_timer(self) -> None:
        self.grading_started_at = None
        self.grading_completed_at = timezone.now()
        self.save(update_fields=["grading_started_at", "grading_completed_at"])

    # transitions assignment grading -> review when no essays are pending or processing
    def check_grading_complete(self) -> None:
        """Transition GRADING -> REVIEW when no essays are PENDING or PROCESSING."""
        if self.status != self.Status.GRADING:
            return
        blocking = self.essays.filter(
            status__in=[Essay.Status.PENDING, Essay.Status.PROCESSING]
        ).exists()
        if not blocking:
            self.status = self.Status.REVIEW
            self.save(update_fields=["status"])
            self.reset_grading_timer()

    def cancel_grading(self) -> None:
        """Revoke the active Celery grading task, if any."""
        if not self.celery_task_id:
            return
        from instagrader.celery import app as celery_app

        celery_app.control.revoke(self.celery_task_id, terminate=True)

    # transitions assignment review -> completed when all essays have been reviewed
    def check_review_complete(self) -> None:
        """Transition REVIEW -> COMPLETED when no essays are GRADED."""
        if self.status != self.Status.REVIEW:
            return
        has_unreviewed = self.essays.filter(status=Essay.Status.GRADED).exists()
        if not has_unreviewed:
            self.status = self.Status.COMPLETED
            self.save(update_fields=["status"])


class Essay(models.Model):
    """A student essay submission."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        GRADED = "graded", "Ready for Review"
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
    failure_reason = models.TextField[str, str](
        blank=True, default="", help_text="Last processing/grading failure reason"
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

    # atomically sets status and failure reason
    def mark_failed(self, reason: str) -> None:
        """Set essay status to FAILED with the given reason and persist."""
        self.status = self.Status.FAILED
        self.failure_reason = reason
        self.save(update_fields=["status", "failure_reason"])
