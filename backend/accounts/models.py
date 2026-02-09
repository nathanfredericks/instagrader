import uuid
from datetime import datetime

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user model for teachers."""

    id = models.UUIDField[uuid.UUID | str, uuid.UUID](
        primary_key=True, default=uuid.uuid4, editable=False
    )
    email = models.EmailField[str, str](unique=True)
    full_name = models.CharField[str, str](max_length=255, blank=True)
    created_at = models.DateTimeField[datetime | str, datetime](auto_now_add=True)
    updated_at = models.DateTimeField[datetime | str, datetime](auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email
