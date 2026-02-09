import uuid
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from assignments.models import Assignment, Essay
from tests.helpers import BaseTestMixin, faker

TEMP_MEDIA = "test_media/"


class GradingTestMixin(BaseTestMixin):
    """Grading-specific test helpers."""

    def create_essay(self, assignment: Assignment, **kwargs: Any) -> Essay:
        defaults: dict[str, Any] = {
            "file_name": f"{faker.word()}.pdf",
            "original_file": SimpleUploadedFile(
                f"{faker.word()}.pdf",
                b"%PDF-1.4 fake content",
                content_type="application/pdf",
            ),
            "extracted_text": faker.paragraph(),
        }
        defaults.update(kwargs)
        return Essay.objects.create(assignment=assignment, **defaults)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class EssayDetailTests(GradingTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.assignment = self.create_assignment(self.user, self.rubric)
        self.essay = self.create_essay(
            self.assignment,
            file_name="alice_essay.pdf",
            extracted_text="This is the extracted essay text content.",
        )

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_assignment = self.create_assignment(
            self.other_user, self.other_rubric
        )
        self.other_essay = self.create_essay(self.other_assignment)

    def detail_url(self, essay_id: uuid.UUID | str) -> str:
        return reverse("essay_detail", kwargs={"essay_id": essay_id})

    def test_detail_requires_auth(self):
        self.client.credentials()
        response = self.client.get(self.detail_url(self.essay.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_success(self):
        response = self.client.get(self.detail_url(self.essay.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_response_keys(self):
        response = self.client.get(self.detail_url(self.essay.id))
        for key in (
            "id",
            "file_name",
            "original_file",
            "extracted_text",
            "status",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, response.data)

    def test_detail_includes_extracted_text(self):
        response = self.client.get(self.detail_url(self.essay.id))
        self.assertEqual(
            response.data["extracted_text"],
            "This is the extracted essay text content.",
        )

    def test_detail_other_user_returns_404(self):
        response = self.client.get(self.detail_url(self.other_essay.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_nonexistent_uuid_returns_404(self):
        response = self.client.get(self.detail_url(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class EssayDeleteTests(GradingTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.assignment = self.create_assignment(self.user, self.rubric)
        self.essay1 = self.create_essay(self.assignment, file_name="essay_one.pdf")
        self.essay2 = self.create_essay(self.assignment, file_name="essay_two.pdf")

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_assignment = self.create_assignment(
            self.other_user, self.other_rubric
        )
        self.other_essay = self.create_essay(self.other_assignment)

    def delete_url(self, essay_id: uuid.UUID | str) -> str:
        return reverse("essay_delete", kwargs={"essay_id": essay_id})

    def test_delete_requires_auth(self):
        self.client.credentials()
        response = self.client.delete(self.delete_url(self.essay1.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_success(self):
        response = self.client.delete(self.delete_url(self.essay1.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Essay.objects.filter(id=self.essay1.id).exists())

    def test_delete_removes_file(self):
        essay_id = self.essay1.id
        self.client.delete(self.delete_url(essay_id))
        self.assertFalse(Essay.objects.filter(id=essay_id).exists())

    def test_delete_other_user_returns_404(self):
        response = self.client.delete(self.delete_url(self.other_essay.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_uuid_returns_404(self):
        response = self.client.delete(self.delete_url(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_does_not_affect_other_essays(self):
        self.client.delete(self.delete_url(self.essay1.id))
        self.assertTrue(Essay.objects.filter(id=self.essay2.id).exists())
