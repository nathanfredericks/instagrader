import uuid

from django.conf import settings
from django.db import models


class Assignment(models.Model):
    """An assignment created by a teacher."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        GRADING = 'grading', 'Grading'
        REVIEW = 'review', 'Review'
        COMPLETED = 'completed', 'Completed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assignments'
    )
    rubric = models.ForeignKey(
        'rubrics.Rubric', on_delete=models.PROTECT, related_name='assignments'
    )
    title = models.CharField(max_length=255)
    prompt = models.TextField(help_text='Writing assignment prompt for AI')
    source_text = models.TextField(
        blank=True, help_text='Reference material for the essay'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Essay(models.Model):
    """A student essay submission."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        GRADED = 'graded', 'Graded'
        REVIEWED = 'reviewed', 'Reviewed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, related_name='essays'
    )
    student_name = models.CharField(max_length=255, help_text='From filename or metadata')
    original_file = models.FileField(upload_to='essays/')
    extracted_text = models.TextField(
        blank=True, help_text='Converted text (via MarkItDown later)'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['student_name']

    def __str__(self):
        return f"{self.student_name} - {self.assignment.title}"
