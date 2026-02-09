from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from faker import Faker
from rest_framework.test import APIClient

from accounts.models import User
from assignments.models import Assignment, Essay
from rubrics.models import Rubric

faker = Faker()
Faker.seed(0)


class BaseTestMixin:
    """Shared helpers for all API tests."""

    password: str
    client: APIClient

    def create_user(
        self, email: str | None = None, password: str | None = None
    ) -> User:
        resolved_email = email or faker.unique.email()
        return User.objects.create_user(
            email=resolved_email,
            username=resolved_email,
            full_name=faker.name(),
            password=password or self.password,
        )

    def login(self, email: str, password: str):
        return self.client.post(
            reverse("login"),
            {"email": email, "password": password},
            format="json",
        )

    def authenticate(self, access_token: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    def auth_user(self, user: User) -> None:
        response = self.login(user.email, self.password)
        self.authenticate(response.data["access"])  # type: ignore[reportUnknownMemberType, reportUnknownArgumentType]

    def create_rubric(self, user: User, **kwargs: Any) -> Rubric:
        defaults: dict[str, Any] = {
            "title": faker.sentence(),
            "description": faker.paragraph(),
        }
        defaults.update(kwargs)
        return Rubric.objects.create(user=user, **defaults)

    def create_assignment(
        self, user: User, rubric: Rubric, **kwargs: Any
    ) -> Assignment:
        defaults: dict[str, Any] = {
            "title": faker.sentence(),
            "prompt": faker.paragraph(),
            "source_text": faker.text(),
        }
        defaults.update(kwargs)
        return Assignment.objects.create(user=user, rubric=rubric, **defaults)

    def create_essay(self, assignment: Assignment, **kwargs: Any) -> Essay:
        defaults: dict[str, Any] = {
            "file_name": f"{faker.word()}.pdf",
            "original_file": SimpleUploadedFile(
                f"{faker.word()}.pdf",
                b"%PDF-1.4 fake content",
                content_type="application/pdf",
            ),
        }
        defaults.update(kwargs)
        return Essay.objects.create(assignment=assignment, **defaults)
