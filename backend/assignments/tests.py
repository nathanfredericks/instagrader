import io
import json
import uuid
import zipfile
from typing import Any
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from assignments.models import Assignment, Essay
from grading.models import CriterionScore, GradingResult
from rubrics.models import CriterionLevel, RubricCriterion
from tests.helpers import BaseTestMixin

TEMP_MEDIA = "test_media/"


class AssignmentTestMixin(BaseTestMixin):
    """Assignment-specific test helpers."""

    def make_test_file(
        self,
        name: str = "essay.pdf",
        content: bytes = b"%PDF-1.4 fake",
        content_type: str = "application/pdf",
    ) -> SimpleUploadedFile:
        return SimpleUploadedFile(name, content, content_type=content_type)

    def make_test_zip(self, files: dict[str, bytes]) -> SimpleUploadedFile:
        """Create an in-memory zip file from a dict of {filename: content_bytes}."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, content in files.items():
                zf.writestr(name, content)
        buf.seek(0)
        return SimpleUploadedFile(
            "essays.zip", buf.read(), content_type="application/zip"
        )

    def make_corrupt_zip(self) -> SimpleUploadedFile:
        return SimpleUploadedFile(
            "corrupt.zip", b"not-a-real-zip-file", content_type="application/zip"
        )


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentListTests(AssignmentTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric(user)

        self.assignments = [self.create_assignment(user, rubric) for _ in range(3)]
        # Add essays to one assignment so we can test essay_count
        self.create_essay(self.assignments[0])
        self.create_essay(self.assignments[0])

        self.url = reverse("assignment_list_create")

    def test_list_requires_auth(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_own_assignments(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {a["id"] for a in response.data}
        own_ids = {str(a.id) for a in self.assignments}
        self.assertEqual(returned_ids, own_ids)

    def test_list_response_keys(self):
        response = self.client.get(self.url)
        item = response.data[0]
        for key in (
            "id",
            "title",
            "description",
            "status",
            "essay_count",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, item)

    def test_list_essay_count_correct(self):
        response = self.client.get(self.url)
        first_assignment = next(
            a for a in response.data if a["id"] == str(self.assignments[0].id)
        )
        self.assertEqual(first_assignment["essay_count"], 2)

    def test_list_empty_for_new_user(self):
        new_user = self.create_user()
        self.auth_user(new_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_list_ordered_by_created_at_desc(self):
        response = self.client.get(self.url)
        dates = [a["created_at"] for a in response.data]
        self.assertEqual(dates, sorted(dates, reverse=True))


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentCreateTests(AssignmentTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        other_user = self.create_user()
        self.auth_user(self.user)
        self.rubric = self.create_rubric(self.user)
        self.other_rubric = self.create_rubric(other_user)
        self.url = reverse("assignment_list_create")

    def test_create_requires_auth(self):
        self.client.credentials()
        payload = {"title": "Test", "prompt": "Write", "rubric": str(self.rubric.id)}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_success(self):
        payload = {
            "title": "Essay Assignment",
            "prompt": "Write a persuasive essay",
            "rubric": str(self.rubric.id),
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assignment = Assignment.objects.get(id=response.data["id"])
        self.assertEqual(assignment.user, self.user)
        self.assertEqual(assignment.title, payload["title"])

    def test_create_response_keys(self):
        payload = {
            "title": "Essay Assignment",
            "prompt": "Write an essay",
            "rubric": str(self.rubric.id),
        }
        response = self.client.post(self.url, payload, format="json")
        for key in (
            "id",
            "rubric",
            "title",
            "description",
            "prompt",
            "source_text",
            "status",
            "essays",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, response.data)

    def test_create_default_status_is_draft(self):
        payload = {
            "title": "Test",
            "prompt": "Write",
            "rubric": str(self.rubric.id),
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.data["status"], "draft")

    def test_create_with_source_text(self):
        payload = {
            "title": "Test",
            "prompt": "Write",
            "rubric": str(self.rubric.id),
            "source_text": "Reference material here",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assignment = Assignment.objects.get(id=response.data["id"])
        self.assertEqual(assignment.source_text, "Reference material here")

    def test_create_with_description(self):
        payload = {
            "title": "Test",
            "description": "Intro assignment",
            "prompt": "Write",
            "rubric": str(self.rubric.id),
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assignment = Assignment.objects.get(id=response.data["id"])
        self.assertEqual(assignment.description, "Intro assignment")

    def test_create_without_source_text(self):
        payload = {
            "title": "Test",
            "prompt": "Write",
            "rubric": str(self.rubric.id),
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assignment = Assignment.objects.get(id=response.data["id"])
        self.assertEqual(assignment.description, "")

    def test_create_missing_title_returns_400(self):
        payload = {"prompt": "Write", "rubric": str(self.rubric.id)}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_prompt_returns_400(self):
        payload = {"title": "Test", "rubric": str(self.rubric.id)}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_rubric_returns_400(self):
        payload = {"title": "Test", "prompt": "Write"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_nonexistent_rubric_returns_400(self):
        payload = {
            "title": "Test",
            "prompt": "Write",
            "rubric": str(uuid.uuid4()),
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_other_user_rubric_returns_400(self):
        payload = {
            "title": "Test",
            "prompt": "Write",
            "rubric": str(self.other_rubric.id),
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_status_ignored_in_payload(self):
        payload = {
            "title": "Test",
            "prompt": "Write",
            "rubric": str(self.rubric.id),
            "status": "completed",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "draft")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentDetailTests(AssignmentTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        user = self.create_user()
        other_user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric(user)
        self.assignment = self.create_assignment(user, rubric)
        self.create_essay(self.assignment, file_name="alice.pdf")
        self.create_essay(self.assignment, file_name="bob.pdf")

        other_rubric = self.create_rubric(other_user)
        self.other_assignment = self.create_assignment(other_user, other_rubric)

    def detail_url(self, assignment_id: uuid.UUID | str) -> str:
        return reverse("assignment_detail", kwargs={"assignment_id": assignment_id})

    def test_detail_requires_auth(self):
        self.client.credentials()
        response = self.client.get(self.detail_url(self.assignment.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_success(self):
        response = self.client.get(self.detail_url(self.assignment.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.assignment.title)

    def test_detail_response_keys(self):
        response = self.client.get(self.detail_url(self.assignment.id))
        for key in (
            "id",
            "rubric",
            "title",
            "description",
            "prompt",
            "source_text",
            "status",
            "essays",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, response.data)

    def test_detail_includes_nested_essays(self):
        response = self.client.get(self.detail_url(self.assignment.id))
        essays = response.data["essays"]
        self.assertEqual(len(essays), 2)
        for essay in essays:
            for key in ("id", "file_name", "status", "created_at"):
                self.assertIn(key, essay)

    def test_detail_other_user_returns_404(self):
        response = self.client.get(self.detail_url(self.other_assignment.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_nonexistent_uuid_returns_404(self):
        response = self.client.get(self.detail_url(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentUpdateTests(AssignmentTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        user = self.create_user()
        other_user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric(user)
        self.rubric2 = self.create_rubric(user)
        self.other_rubric = self.create_rubric(other_user)

        self.assignment = self.create_assignment(
            user,
            rubric,
            title="Original Title",
            description="Original Description",
            prompt="Original Prompt",
            source_text="Original Source",
        )
        self.other_assignment = self.create_assignment(other_user, self.other_rubric)

    def detail_url(self, assignment_id: uuid.UUID | str) -> str:
        return reverse("assignment_detail", kwargs={"assignment_id": assignment_id})

    def test_update_requires_auth(self):
        self.client.credentials()
        response = self.client.patch(
            self.detail_url(self.assignment.id), {"title": "New"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_title_success(self):
        response = self.client.patch(
            self.detail_url(self.assignment.id), {"title": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.title, "Updated")

    def test_update_prompt_success(self):
        response = self.client.patch(
            self.detail_url(self.assignment.id), {"prompt": "New prompt"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.prompt, "New prompt")

    def test_update_source_text_success(self):
        response = self.client.patch(
            self.detail_url(self.assignment.id),
            {"source_text": "New source"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.source_text, "New source")

    def test_update_description_success(self):
        response = self.client.patch(
            self.detail_url(self.assignment.id),
            {"description": "New description"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.description, "New description")

    def test_update_partial_does_not_clear_other_fields(self):
        self.client.patch(
            self.detail_url(self.assignment.id), {"title": "Changed"}, format="json"
        )
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.description, "Original Description")
        self.assertEqual(self.assignment.prompt, "Original Prompt")
        self.assertEqual(self.assignment.source_text, "Original Source")

    def test_update_status_ignored(self):
        self.client.patch(
            self.detail_url(self.assignment.id),
            {"status": "completed"},
            format="json",
        )
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.Status.DRAFT)

    def test_update_rubric_to_own_rubric_success(self):
        response = self.client.patch(
            self.detail_url(self.assignment.id),
            {"rubric": str(self.rubric2.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.rubric, self.rubric2)

    def test_update_rubric_to_other_user_rubric_returns_400(self):
        response = self.client.patch(
            self.detail_url(self.assignment.id),
            {"rubric": str(self.other_rubric.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_other_user_returns_404(self):
        response = self.client.patch(
            self.detail_url(self.other_assignment.id),
            {"title": "Hack"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_nonexistent_uuid_returns_404(self):
        response = self.client.patch(
            self.detail_url(uuid.uuid4()), {"title": "Nope"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentDeleteTests(AssignmentTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        user = self.create_user()
        other_user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric(user)
        self.assignment = self.create_assignment(user, rubric)
        self.essay = self.create_essay(self.assignment)

        other_rubric = self.create_rubric(other_user)
        self.other_assignment = self.create_assignment(other_user, other_rubric)

    def detail_url(self, assignment_id: uuid.UUID | str) -> str:
        return reverse("assignment_detail", kwargs={"assignment_id": assignment_id})

    def test_delete_requires_auth(self):
        self.client.credentials()
        response = self.client.delete(self.detail_url(self.assignment.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_success(self):
        response = self.client.delete(self.detail_url(self.assignment.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Assignment.objects.filter(id=self.assignment.id).exists())

    def test_delete_cascades_essays(self):
        essay_id = self.essay.id
        self.client.delete(self.detail_url(self.assignment.id))
        self.assertFalse(Essay.objects.filter(id=essay_id).exists())

    def test_delete_other_user_returns_404(self):
        response = self.client.delete(self.detail_url(self.other_assignment.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_uuid_returns_404(self):
        response = self.client.delete(self.detail_url(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentUploadTests(AssignmentTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        user = self.create_user()
        other_user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric(user)
        self.assignment = self.create_assignment(user, rubric)

        other_rubric = self.create_rubric(other_user)
        self.other_assignment = self.create_assignment(other_user, other_rubric)

    def upload_url(self, assignment_id: uuid.UUID | str) -> str:
        return reverse("assignment_upload", kwargs={"assignment_id": assignment_id})

    def test_upload_requires_auth(self):
        self.client.credentials()
        f = self.make_test_file()
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_single_pdf_success(self, mock_task: MagicMock):
        f = self.make_test_file(
            "student_essay.pdf", b"%PDF-1.4 content", "application/pdf"
        )
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Essay.objects.filter(assignment=self.assignment).count(), 1)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_single_docx_success(self, mock_task: MagicMock):
        f = self.make_test_file(
            "essay.docx",
            b"PK\x03\x04 fake docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_single_txt_success(self, mock_task: MagicMock):
        f = self.make_test_file("essay.txt", b"This is my essay.", "text/plain")
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_dispatches_celery_task(self, mock_task: MagicMock):
        f = self.make_test_file()
        self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        mock_task.assert_called_once()

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_celery_task_receives_essay_ids(self, mock_task: MagicMock):
        f = self.make_test_file()
        self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        call_args = mock_task.call_args
        essay_ids = call_args[0][0] if call_args[0] else call_args[1].get("essay_ids")
        essay = Essay.objects.filter(assignment=self.assignment).first()
        assert essay is not None
        self.assertIn(str(essay.id), [str(eid) for eid in essay_ids])

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_sets_status_to_pending(self, mock_task: MagicMock):
        f = self.make_test_file()
        self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        essay = Essay.objects.filter(assignment=self.assignment).first()
        assert essay is not None
        self.assertEqual(essay.status, Essay.Status.PENDING)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_zip_multiple_valid_files(self, mock_task: MagicMock):
        zf = self.make_test_zip(
            {
                "essay1.pdf": b"%PDF-1.4 fake",
                "essay2.docx": b"PK fake docx",
                "essay3.txt": b"plain text essay",
            }
        )
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": zf}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Essay.objects.filter(assignment=self.assignment).count(), 3)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_zip_extracts_file_names(self, mock_task: MagicMock):
        zf = self.make_test_zip(
            {
                "alice_essay.pdf": b"%PDF-1.4 fake",
                "bob_essay.txt": b"plain text",
            }
        )
        self.client.post(
            self.upload_url(self.assignment.id), {"files": zf}, format="multipart"
        )
        file_names = set(
            Essay.objects.filter(assignment=self.assignment).values_list(
                "file_name", flat=True
            )
        )
        self.assertIn("alice_essay.pdf", file_names)
        self.assertIn("bob_essay.txt", file_names)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_zip_single_file(self, mock_task: MagicMock):
        zf = self.make_test_zip({"only_one.pdf": b"%PDF-1.4 fake"})
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": zf}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Essay.objects.filter(assignment=self.assignment).count(), 1)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_zip_ignores_macosx_metadata(self, mock_task: MagicMock):
        zf = self.make_test_zip(
            {
                "essay.pdf": b"%PDF-1.4 fake",
                "__MACOSX/._essay.pdf": b"mac metadata",
                ".DS_Store": b"ds store data",
            }
        )
        self.client.post(
            self.upload_url(self.assignment.id), {"files": zf}, format="multipart"
        )
        self.assertEqual(Essay.objects.filter(assignment=self.assignment).count(), 1)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_zip_ignores_hidden_files(self, mock_task: MagicMock):
        zf = self.make_test_zip(
            {
                "essay.pdf": b"%PDF-1.4 fake",
                ".hidden_file.pdf": b"hidden",
            }
        )
        self.client.post(
            self.upload_url(self.assignment.id), {"files": zf}, format="multipart"
        )
        self.assertEqual(Essay.objects.filter(assignment=self.assignment).count(), 1)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_zip_nested_directories(self, mock_task: MagicMock):
        zf = self.make_test_zip(
            {
                "folder/essay1.pdf": b"%PDF-1.4 fake",
                "folder/subfolder/essay2.txt": b"text content",
            }
        )
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": zf}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Essay.objects.filter(assignment=self.assignment).count(), 2)

    def test_upload_empty_zip_returns_400(self):
        zf = self.make_test_zip({})
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": zf}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_corrupt_zip_returns_400(self):
        f = self.make_corrupt_zip()
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_zip_only_invalid_types_returns_400(self):
        zf = self.make_test_zip(
            {
                "photo.jpg": b"\xff\xd8\xff fake jpg",
                "program.exe": b"MZ fake exe",
            }
        )
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": zf}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_zip_mixed_valid_and_invalid(self, mock_task: MagicMock):
        zf = self.make_test_zip(
            {
                "essay.pdf": b"%PDF-1.4 fake",
                "notes.txt": b"plain text",
                "photo.jpg": b"\xff\xd8\xff fake jpg",
            }
        )
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": zf}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Essay.objects.filter(assignment=self.assignment).count(), 2)

    def test_upload_unsupported_file_type_returns_400(self):
        f = self.make_test_file("photo.jpg", b"\xff\xd8\xff fake", "image/jpeg")
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_no_file_returns_400(self):
        response = self.client.post(
            self.upload_url(self.assignment.id), {}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_empty_file_returns_400(self):
        f = self.make_test_file("empty.pdf", b"", "application/pdf")
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_other_user_assignment_returns_404(self):
        f = self.make_test_file()
        response = self.client.post(
            self.upload_url(self.other_assignment.id), {"files": f}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_upload_nonexistent_assignment_returns_404(self):
        f = self.make_test_file()
        response = self.client.post(
            self.upload_url(uuid.uuid4()), {"files": f}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_response_contains_essay_list(self, mock_task: MagicMock):
        f = self.make_test_file()
        response = self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
        for essay_data in response.data:
            self.assertIn("id", essay_data)
            self.assertIn("file_name", essay_data)
            self.assertIn("status", essay_data)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_multiple_individual_files(self, mock_task: MagicMock):
        f1 = self.make_test_file("essay1.pdf", b"%PDF-1.4 first", "application/pdf")
        f2 = self.make_test_file("essay2.txt", b"Second essay text", "text/plain")
        response = self.client.post(
            self.upload_url(self.assignment.id),
            {"files": [f1, f2]},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Essay.objects.filter(assignment=self.assignment).count(), 2)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_stores_original_file(self, mock_task: MagicMock):
        f = self.make_test_file("my_essay.pdf", b"%PDF-1.4 content", "application/pdf")
        self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        essay = Essay.objects.filter(assignment=self.assignment).first()
        assert essay is not None
        self.assertTrue(essay.original_file)
        self.assertTrue(essay.original_file.name)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_file_name_derived_from_filename(self, mock_task: MagicMock):
        f = self.make_test_file(
            "alice_homework.pdf", b"%PDF-1.4 content", "application/pdf"
        )
        self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        essay = Essay.objects.filter(assignment=self.assignment).first()
        assert essay is not None
        self.assertEqual(essay.file_name, "alice_homework.pdf")

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_sets_grading_timer(self, mock_task: MagicMock):
        f = self.make_test_file()
        self.client.post(
            self.upload_url(self.assignment.id), {"files": f}, format="multipart"
        )
        self.assignment.refresh_from_db()
        self.assertIsNotNone(self.assignment.grading_started_at)
        self.assertIsNone(self.assignment.grading_completed_at)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentEssaysListTests(AssignmentTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        user = self.create_user()
        other_user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric(user)
        self.assignment = self.create_assignment(user, rubric)
        self.create_essay(self.assignment, file_name="alice.pdf")
        self.create_essay(self.assignment, file_name="bob.pdf")
        self.create_essay(self.assignment, file_name="charlie.pdf")

        self.empty_assignment = self.create_assignment(user, rubric)

        other_rubric = self.create_rubric(other_user)
        self.other_assignment = self.create_assignment(other_user, other_rubric)

    def essays_url(self, assignment_id: uuid.UUID | str) -> str:
        return reverse("assignment_essays", kwargs={"assignment_id": assignment_id})

    def test_list_essays_requires_auth(self):
        self.client.credentials()
        response = self.client.get(self.essays_url(self.assignment.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_essays_success(self):
        response = self.client.get(self.essays_url(self.assignment.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_list_essays_response_keys(self):
        response = self.client.get(self.essays_url(self.assignment.id))
        essay = response.data[0]
        for key in ("id", "file_name", "status", "created_at"):
            self.assertIn(key, essay)

    def test_list_essays_excludes_extracted_text(self):
        response = self.client.get(self.essays_url(self.assignment.id))
        essay = response.data[0]
        self.assertNotIn("extracted_text", essay)

    def test_list_essays_empty_assignment(self):
        response = self.client.get(self.essays_url(self.empty_assignment.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_list_essays_other_user_returns_404(self):
        response = self.client.get(self.essays_url(self.other_assignment.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_essays_nonexistent_assignment_returns_404(self):
        response = self.client.get(self.essays_url(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_essays_ordered_by_file_name(self):
        response = self.client.get(self.essays_url(self.assignment.id))
        file_names = [e["file_name"] for e in response.data]
        self.assertEqual(file_names, sorted(file_names))


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentExportCSVTests(AssignmentTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.assignment = self.create_assignment(self.user, self.rubric)
        self.create_essay(self.assignment, file_name="alice.pdf")
        self.create_essay(self.assignment, file_name="bob.pdf")
        self.create_essay(self.assignment, file_name="charlie.pdf")

        self.empty_assignment = self.create_assignment(self.user, self.rubric)

        other_rubric = self.create_rubric(other_user)
        self.other_assignment = self.create_assignment(other_user, other_rubric)

    def csv_url(self, assignment_id: uuid.UUID | str) -> str:
        return reverse("assignment_export_csv", kwargs={"assignment_id": assignment_id})

    def test_export_csv_requires_auth(self):
        self.client.credentials()
        response = self.client.get(self.csv_url(self.assignment.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_export_csv_success(self):
        response = self.client.get(self.csv_url(self.assignment.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_export_csv_content_disposition(self):
        response = self.client.get(self.csv_url(self.assignment.id))
        self.assertIn("Content-Disposition", response)
        self.assertIn(".csv", response["Content-Disposition"])
        self.assertIn("attachment", response["Content-Disposition"])

    def test_export_csv_has_correct_headers(self):
        response = self.client.get(self.csv_url(self.assignment.id))
        content = response.content.decode("utf-8")
        first_line = content.split("\n")[0]
        self.assertIn("file_name", first_line.lower())

    def test_export_csv_correct_row_count(self):
        response = self.client.get(self.csv_url(self.assignment.id))
        content = response.content.decode("utf-8")
        rows = [r for r in content.strip().split("\n") if r]
        # 1 header + 3 essays = 4 rows
        self.assertEqual(len(rows), 4)

    def test_export_csv_empty_assignment(self):
        response = self.client.get(self.csv_url(self.empty_assignment.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode("utf-8")
        rows = [r for r in content.strip().split("\n") if r]
        # Just the header row
        self.assertEqual(len(rows), 1)

    def test_export_csv_other_user_returns_404(self):
        response = self.client.get(self.csv_url(self.other_assignment.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_export_csv_nonexistent_assignment_returns_404(self):
        response = self.client.get(self.csv_url(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_export_csv_sanitizes_filename_quotes(self):
        assignment = self.create_assignment(
            self.user, self.rubric, title='My "Special" Assignment'
        )
        response = self.client.get(self.csv_url(assignment.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Special"', response["Content-Disposition"])

    def test_export_csv_sanitizes_filename_newlines(self):
        assignment = self.create_assignment(
            self.user, self.rubric, title="Title\r\nInjected-Header: value"
        )
        response = self.client.get(self.csv_url(assignment.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("\n", response["Content-Disposition"])
        self.assertNotIn("\r", response["Content-Disposition"])


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentExportPDFTests(AssignmentTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        user = self.create_user()
        other_user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric(user)
        self.assignment = self.create_assignment(user, rubric)
        self.essay = self.create_essay(self.assignment)

        other_rubric = self.create_rubric(other_user)
        self.other_assignment = self.create_assignment(other_user, other_rubric)
        self.other_essay = self.create_essay(self.other_assignment)

        # An essay on a different assignment of the same user
        assignment2 = self.create_assignment(user, rubric)
        self.essay_different_assignment = self.create_essay(assignment2)

    def pdf_url(self, assignment_id: uuid.UUID | str, essay_id: uuid.UUID | str) -> str:
        return reverse(
            "assignment_export_pdf",
            kwargs={"assignment_id": assignment_id, "essay_id": essay_id},
        )

    def test_export_pdf_requires_auth(self):
        self.client.credentials()
        response = self.client.get(self.pdf_url(self.assignment.id, self.essay.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_export_pdf_success(self):
        response = self.client.get(self.pdf_url(self.assignment.id, self.essay.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_export_pdf_content_disposition(self):
        response = self.client.get(self.pdf_url(self.assignment.id, self.essay.id))
        self.assertIn("Content-Disposition", response)
        self.assertIn(".pdf", response["Content-Disposition"])

    def test_export_pdf_other_user_returns_404(self):
        response = self.client.get(
            self.pdf_url(self.other_assignment.id, self.other_essay.id)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_export_pdf_nonexistent_assignment_returns_404(self):
        response = self.client.get(self.pdf_url(uuid.uuid4(), self.essay.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_export_pdf_nonexistent_essay_returns_404(self):
        response = self.client.get(self.pdf_url(self.assignment.id, uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_export_pdf_essay_wrong_assignment_returns_404(self):
        response = self.client.get(
            self.pdf_url(self.assignment.id, self.essay_different_assignment.id)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_export_docx_content_type(self):
        docx_essay = self.create_essay(
            self.assignment,
            file_name="essay.docx",
            original_file=SimpleUploadedFile(
                "essay.docx",
                b"PK fake docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        )
        response = self.client.get(self.pdf_url(self.assignment.id, docx_essay.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            response["Content-Type"],
        )

    def test_export_txt_content_type(self):
        txt_essay = self.create_essay(
            self.assignment,
            file_name="essay.txt",
            original_file=SimpleUploadedFile(
                "essay.txt", b"Plain text content", content_type="text/plain"
            ),
        )
        response = self.client.get(self.pdf_url(self.assignment.id, txt_essay.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/plain", response["Content-Type"])

    def test_export_uses_original_filename(self):
        response = self.client.get(self.pdf_url(self.assignment.id, self.essay.id))
        self.assertIn(self.essay.file_name, response["Content-Disposition"])
        self.assertNotIn(".pdf.pdf", response["Content-Disposition"])


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class CeleryEssayProcessingTests(AssignmentTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        user = self.create_user()
        self.auth_user(user)
        rubric = self.create_rubric(user)
        self.assignment = self.create_assignment(user, rubric)

    def test_task_is_importable(self):
        from assignments.tasks import process_essay_batch

        self.assertTrue(callable(process_essay_batch))

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_endpoint_dispatches_task_with_delay(self, mock_delay: MagicMock):
        f = self.make_test_file()
        self.client.post(
            reverse("assignment_upload", kwargs={"assignment_id": self.assignment.id}),
            {"files": f},
            format="multipart",
        )
        mock_delay.assert_called_once()

    @patch("grading.bedrock.wait_for_model")
    @patch("assignments.tasks.chord")
    def test_task_dispatches_parallel_essay_workflows(
        self, mock_chord: MagicMock, mock_wait: MagicMock
    ):
        from assignments.tasks import process_essay_batch

        essay = self.create_essay(self.assignment)
        chord_signature = MagicMock()
        mock_chord.return_value = chord_signature

        process_essay_batch([str(essay.id)])

        mock_wait.assert_called_once()
        mock_chord.assert_called_once()
        workflows = mock_chord.call_args[0][0]
        self.assertEqual(len(workflows), 1)
        chord_signature.assert_called_once()

    @patch("grading.bedrock.wait_for_model")
    @patch("assignments.tasks.chord")
    def test_task_processes_multiple_essays(self, mock_chord: MagicMock, mock_wait):
        from assignments.tasks import process_essay_batch

        essays = [
            self.create_essay(
                self.assignment,
                original_file=SimpleUploadedFile(
                    f"essay{i}.txt", f"Content {i}".encode(), content_type="text/plain"
                ),
            )
            for i in range(3)
        ]
        chord_signature = MagicMock()
        mock_chord.return_value = chord_signature

        process_essay_batch([str(e.id) for e in essays])

        mock_wait.assert_called_once()
        mock_chord.assert_called_once()
        workflows = mock_chord.call_args[0][0]
        self.assertEqual(len(workflows), 3)
        chord_signature.assert_called_once()

    @patch("grading.bedrock.wait_for_model")
    @patch("assignments.tasks.chord")
    def test_task_skips_nonexistent_essay(self, mock_chord: MagicMock, _mock_wait):
        from assignments.tasks import process_essay_batch

        essay = self.create_essay(self.assignment)
        chord_signature = MagicMock()
        mock_chord.return_value = chord_signature

        process_essay_batch([str(uuid.uuid4()), str(essay.id)])

        mock_chord.assert_called_once()
        workflows = mock_chord.call_args[0][0]
        self.assertEqual(len(workflows), 1)
        chord_signature.assert_called_once()

    def test_task_sets_failed_status_on_extraction_error(self):
        from assignments.tasks import extract_essay_text

        essay = self.create_essay(
            self.assignment,
            original_file=SimpleUploadedFile(
                "test.pdf", b"%PDF-1.4 fake", content_type="application/pdf"
            ),
        )
        with patch("assignments.tasks.MarkItDown") as mock_md:
            mock_md.return_value.convert.side_effect = RuntimeError("conversion failed")
            extract_essay_text(str(essay.id))
        essay.refresh_from_db()
        self.assertEqual(essay.status, Essay.Status.FAILED)

    def test_task_extracts_from_pdf(self):
        from assignments.tasks import extract_essay_text

        essay = self.create_essay(
            self.assignment,
            original_file=SimpleUploadedFile(
                "test.pdf", b"%PDF-1.4 content", content_type="application/pdf"
            ),
        )
        extract_essay_text(str(essay.id))
        essay.refresh_from_db()
        self.assertIsNotNone(essay.extracted_text)

    def test_task_extracts_from_docx(self):
        from assignments.tasks import extract_essay_text

        essay = self.create_essay(
            self.assignment,
            original_file=SimpleUploadedFile(
                "test.docx",
                b"PK fake docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        )
        extract_essay_text(str(essay.id))
        essay.refresh_from_db()
        self.assertIsNotNone(essay.extracted_text)

    def test_task_extracts_from_txt(self):
        from assignments.tasks import extract_essay_text

        essay = self.create_essay(
            self.assignment,
            original_file=SimpleUploadedFile(
                "test.txt", b"Plain text essay content.", content_type="text/plain"
            ),
        )
        extract_essay_text(str(essay.id))
        essay.refresh_from_db()
        self.assertIn("Plain text essay content", essay.extracted_text)


class GradingTestHelperMixin(AssignmentTestMixin):
    """Helpers for grading-related assignment tests."""

    def create_rubric_with_criteria(self, user: Any):
        rubric = self.create_rubric(user)
        c1 = RubricCriterion.objects.create(rubric=rubric, name="Thesis", order=0)
        CriterionLevel.objects.create(criterion=c1, score=1, descriptor="Weak")
        CriterionLevel.objects.create(criterion=c1, score=2, descriptor="Adequate")
        CriterionLevel.objects.create(criterion=c1, score=3, descriptor="Strong")
        c2 = RubricCriterion.objects.create(rubric=rubric, name="Evidence", order=1)
        CriterionLevel.objects.create(criterion=c2, score=1, descriptor="Weak")
        CriterionLevel.objects.create(criterion=c2, score=2, descriptor="Adequate")
        CriterionLevel.objects.create(criterion=c2, score=3, descriptor="Strong")
        return rubric

    def _make_bedrock_response(self, criteria):
        """Build a canned Bedrock JSON response matching the given criteria."""
        from grading.bedrock import build_model_id_mapping

        model_id_mapping = build_model_id_mapping(criteria)
        criteria_by_uuid = {criterion.id: criterion for criterion in criteria}
        scores = []
        for criteria_id in sorted(model_id_mapping.criterion_numeric_to_uuid.keys()):
            criterion_uuid = model_id_mapping.criterion_numeric_to_uuid[criteria_id]
            criterion = criteria_by_uuid[criterion_uuid]
            level_id = min(
                model_id_mapping.level_numeric_to_uuid_by_criterion[criteria_id].keys()
            )
            scores.append(
                {
                    "criteria_id": criteria_id,
                    "level_id": level_id,
                    "feedback": f"Feedback for {criterion.name}.",
                }
            )
        return json.dumps({"scores": scores})


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class GradeEssayTaskTests(GradingTestHelperMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        user = self.create_user()
        self.auth_user(user)
        rubric = self.create_rubric_with_criteria(user)
        self.assignment = self.create_assignment(
            user, rubric, status=Assignment.Status.GRADING
        )
        self.criteria = list(rubric.criteria.prefetch_related("levels").all())

    def test_grade_essay_creates_grading_result(self):
        from assignments.tasks import grade_essay

        essay = self.create_essay(self.assignment, extracted_text="My essay text.")
        canned = self._make_bedrock_response(self.criteria)
        with patch("grading.bedrock.call_bedrock", return_value=canned):
            grade_essay(str(essay.id))

        self.assertTrue(GradingResult.objects.filter(essay=essay).exists())
        grading_result = GradingResult.objects.get(essay=essay)
        self.assertEqual(grading_result.criterion_scores.count(), 2)

    def test_grade_essay_sets_status_graded(self):
        from assignments.tasks import grade_essay

        essay = self.create_essay(self.assignment, extracted_text="My essay text.")
        canned = self._make_bedrock_response(self.criteria)
        with patch("grading.bedrock.call_bedrock", return_value=canned):
            grade_essay(str(essay.id))

        essay.refresh_from_db()
        self.assertEqual(essay.status, Essay.Status.GRADED)

    def test_grade_essay_maps_numeric_model_ids_to_uuid_foreign_keys(self):
        from assignments.tasks import grade_essay

        essay = self.create_essay(self.assignment, extracted_text="My essay text.")
        canned = self._make_bedrock_response(self.criteria)
        with patch("grading.bedrock.call_bedrock", return_value=canned):
            grade_essay(str(essay.id))

        grading_result = GradingResult.objects.get(essay=essay)
        criterion_score = grading_result.criterion_scores.first()
        self.assertIsNotNone(criterion_score)

        rubric_criterion_ids = {criterion.id for criterion in self.criteria}
        rubric_level_ids = {
            level.id for criterion in self.criteria for level in criterion.levels.all()
        }
        self.assertIn(criterion_score.criterion_id, rubric_criterion_ids)
        self.assertIn(criterion_score.level_id, rubric_level_ids)

    def test_grade_essay_failure_sets_status_failed(self):
        from assignments.tasks import grade_essay

        essay = self.create_essay(self.assignment, extracted_text="My essay text.")
        with patch(
            "grading.bedrock.call_bedrock",
            side_effect=RuntimeError("Bedrock error"),
        ):
            grade_essay(str(essay.id))

        essay.refresh_from_db()
        self.assertEqual(essay.status, Essay.Status.FAILED)
        self.assertFalse(GradingResult.objects.filter(essay=essay).exists())

    def test_grade_essay_no_text_sets_failed(self):
        from assignments.tasks import grade_essay

        essay = self.create_essay(self.assignment, extracted_text="")
        grade_essay(str(essay.id))
        essay.refresh_from_db()
        self.assertEqual(essay.status, Essay.Status.FAILED)

    def test_grade_essay_invalid_model_output_retries_and_sets_parser_reason(self):
        from assignments.tasks import grade_essay

        essay = self.create_essay(self.assignment, extracted_text="My essay text.")
        invalid_response = json.dumps({"scores": []})
        with patch(
            "grading.bedrock.call_bedrock", return_value=invalid_response
        ) as mock_call:
            grade_essay(str(essay.id))

        essay.refresh_from_db()
        self.assertEqual(mock_call.call_count, 3)
        self.assertEqual(essay.status, Essay.Status.FAILED)
        self.assertIn("Model response validation failed:", essay.failure_reason)
        self.assertIn("missing scores for criteria_id", essay.failure_reason)
        self.assertFalse(GradingResult.objects.filter(essay=essay).exists())

    def test_grade_essay_does_not_call_check_grading_complete(self):
        """grade_essay no longer triggers check_grading_complete (batch does)."""
        from assignments.tasks import grade_essay

        essay = self.create_essay(self.assignment, extracted_text="My essay text.")
        canned = self._make_bedrock_response(self.criteria)
        with patch("grading.bedrock.call_bedrock", return_value=canned):
            grade_essay(str(essay.id))

        # Assignment should still be GRADING -- batch is responsible for the transition
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.Status.GRADING)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProcessBatchRetryTests(GradingTestHelperMixin, APITestCase):
    """Tests for batch-level model readiness and grading flow."""

    def setUp(self):
        self.password = "TestPassword123!"
        user = self.create_user()
        self.auth_user(user)
        rubric = self.create_rubric_with_criteria(user)
        self.assignment = self.create_assignment(
            user, rubric, status=Assignment.Status.GRADING
        )
        self.criteria = list(rubric.criteria.prefetch_related("levels").all())

    @patch("grading.bedrock.wait_for_model")
    @patch("assignments.tasks.chord")
    def test_process_batch_waits_for_model(self, mock_chord: MagicMock, mock_wait):
        """wait_for_model is called once, then one workflow per essay is dispatched."""
        from assignments.tasks import process_essay_batch

        essays = [
            self.create_essay(
                self.assignment,
                original_file=SimpleUploadedFile(
                    f"essay{i}.txt",
                    f"Content {i}".encode(),
                    content_type="text/plain",
                ),
            )
            for i in range(3)
        ]
        chord_signature = MagicMock()
        mock_chord.return_value = chord_signature

        process_essay_batch([str(e.id) for e in essays])

        mock_wait.assert_called_once()
        mock_chord.assert_called_once()
        workflows = mock_chord.call_args[0][0]
        self.assertEqual(len(workflows), len(essays))
        chord_signature.assert_called_once()

    @patch("grading.bedrock.wait_for_model")
    @patch("assignments.tasks.chord")
    def test_process_batch_marks_pending_failed_when_model_unavailable(
        self, mock_chord: MagicMock, mock_wait
    ):
        """Terminal preflight failures fail pending essays and unblock assignment."""
        from assignments.tasks import process_essay_batch
        from grading.bedrock import ModelUnavailableError

        raw_error = (
            "An error occurred (ModelErrorException) when calling the InvokeModel "
            "operation: The request failed in the model container."
        )
        mock_wait.side_effect = ModelUnavailableError(raw_error)

        # Existing graded work should still allow assignment to move to REVIEW
        self.create_essay(self.assignment, status=Essay.Status.GRADED)
        essays = [
            self.create_essay(
                self.assignment,
                original_file=SimpleUploadedFile(
                    f"essay{i}.txt",
                    f"Content {i}".encode(),
                    content_type="text/plain",
                ),
            )
            for i in range(2)
        ]

        process_essay_batch([str(e.id) for e in essays])

        for essay in essays:
            essay.refresh_from_db()
            self.assertEqual(essay.status, Essay.Status.FAILED)
            self.assertEqual(essay.failure_reason, raw_error)

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.Status.REVIEW)
        mock_chord.assert_not_called()

    @patch("grading.bedrock.wait_for_model")
    @patch("assignments.tasks.chord")
    def test_process_batch_marks_pending_failed_on_unexpected_preflight_error(
        self, mock_chord: MagicMock, mock_wait
    ):
        """Unexpected preflight errors still fail pending essays before re-raising."""
        from assignments.tasks import process_essay_batch

        mock_wait.side_effect = RuntimeError("Probe crashed unexpectedly")

        essays = [
            self.create_essay(
                self.assignment,
                original_file=SimpleUploadedFile(
                    f"essay{i}.txt",
                    f"Content {i}".encode(),
                    content_type="text/plain",
                ),
            )
            for i in range(2)
        ]

        with self.assertRaises(RuntimeError):
            process_essay_batch([str(e.id) for e in essays])

        for essay in essays:
            essay.refresh_from_db()
            self.assertEqual(essay.status, Essay.Status.FAILED)
            self.assertEqual(essay.failure_reason, "Probe crashed unexpectedly")

        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.Status.REVIEW)
        mock_chord.assert_not_called()


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentStatusTransitionTests(GradingTestHelperMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.auth_user(self.user)
        self.rubric = self.create_rubric_with_criteria(self.user)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_upload_transitions_draft_to_grading(self, mock_delay: MagicMock):
        assignment = self.create_assignment(self.user, self.rubric)
        self.assertEqual(assignment.status, Assignment.Status.DRAFT)

        f = self.make_test_file()
        self.client.post(
            reverse("assignment_upload", kwargs={"assignment_id": assignment.id}),
            {"files": f},
            format="multipart",
        )
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.GRADING)

    def test_grading_to_review_when_all_graded(self):
        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.GRADING
        )
        assignment.grading_started_at = timezone.now()
        assignment.save(update_fields=["grading_started_at"])
        self.create_essay(assignment, status=Essay.Status.GRADED)
        self.create_essay(assignment, status=Essay.Status.FAILED)

        assignment.check_grading_complete()
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.REVIEW)
        self.assertIsNone(assignment.grading_started_at)
        self.assertIsNotNone(assignment.grading_completed_at)

    def test_grading_blocked_by_pending_essay(self):
        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.GRADING
        )
        assignment.grading_started_at = timezone.now()
        assignment.save(update_fields=["grading_started_at"])
        self.create_essay(assignment, status=Essay.Status.GRADED)
        self.create_essay(assignment, status=Essay.Status.PENDING)

        assignment.check_grading_complete()
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.GRADING)
        self.assertIsNotNone(assignment.grading_started_at)

    def test_review_to_completed_when_all_reviewed(self):
        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.REVIEW
        )
        self.create_essay(assignment, status=Essay.Status.REVIEWED)
        self.create_essay(assignment, status=Essay.Status.FAILED)

        assignment.check_review_complete()
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.COMPLETED)

    def test_review_blocked_by_graded_essay(self):
        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.REVIEW
        )
        self.create_essay(assignment, status=Essay.Status.REVIEWED)
        self.create_essay(assignment, status=Essay.Status.GRADED)

        assignment.check_review_complete()
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.REVIEW)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentExportCSVWithGradesTests(GradingTestHelperMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        user = self.create_user()
        self.auth_user(user)
        rubric = self.create_rubric_with_criteria(user)
        self.assignment = self.create_assignment(user, rubric)

        self.criteria = list(rubric.criteria.prefetch_related("levels").all())
        self.essay = self.create_essay(
            self.assignment,
            file_name="graded_essay.pdf",
            status=Essay.Status.GRADED,
        )
        self.grading_result = GradingResult.objects.create(essay=self.essay)
        for criterion in self.criteria:
            level = criterion.levels.first()
            CriterionScore.objects.create(
                grading_result=self.grading_result,
                criterion=criterion,
                level=level,
                feedback=f"AI feedback for {criterion.name}.",
            )

    def csv_url(self, assignment_id):
        return reverse("assignment_export_csv", kwargs={"assignment_id": assignment_id})

    def _parse_csv(self, response):
        import csv as csv_mod
        import io

        content = response.content.decode("utf-8")
        reader = csv_mod.reader(io.StringIO(content))
        return list(reader)

    def test_csv_header_includes_criteria_columns(self):
        response = self.client.get(self.csv_url(self.assignment.id))
        rows = self._parse_csv(response)
        header = rows[0]
        self.assertIn("Thesis (score)", header)
        self.assertIn("Thesis (feedback)", header)
        self.assertIn("Evidence (score)", header)
        self.assertIn("Evidence (feedback)", header)
        self.assertIn("total_score", header)

    def test_csv_includes_ai_scores(self):
        response = self.client.get(self.csv_url(self.assignment.id))
        rows = self._parse_csv(response)
        header = rows[0]
        data_row = rows[1]
        score_idx = header.index("Thesis (score)")
        self.assertEqual(data_row[score_idx], "1")
        feedback_idx = header.index("Thesis (feedback)")
        self.assertIn("AI feedback", data_row[feedback_idx])

    def test_csv_uses_teacher_override_when_present(self):
        score = self.grading_result.criterion_scores.first()
        criterion = score.criterion
        teacher_level = criterion.levels.last()
        score.teacher_level = teacher_level
        score.teacher_feedback = "Teacher override feedback."
        score.save()

        response = self.client.get(self.csv_url(self.assignment.id))
        rows = self._parse_csv(response)
        header = rows[0]
        data_row = rows[1]
        score_idx = header.index(f"{criterion.name} (score)")
        self.assertEqual(data_row[score_idx], str(teacher_level.score))
        feedback_idx = header.index(f"{criterion.name} (feedback)")
        self.assertEqual(data_row[feedback_idx], "Teacher override feedback.")

    def test_csv_empty_columns_for_ungraded_essay(self):
        self.create_essay(
            self.assignment,
            file_name="ungraded.pdf",
            status=Essay.Status.PENDING,
        )
        response = self.client.get(self.csv_url(self.assignment.id))
        rows = self._parse_csv(response)
        header = rows[0]
        # Find the ungraded essay row
        for row in rows[1:]:
            if row[0] == "ungraded.pdf":
                score_idx = header.index("Thesis (score)")
                self.assertEqual(row[score_idx], "")
                total_idx = header.index("total_score")
                self.assertEqual(row[total_idx], "")
                break
        else:
            self.fail("Ungraded essay not found in CSV")

    def test_csv_total_score_is_sum(self):
        response = self.client.get(self.csv_url(self.assignment.id))
        rows = self._parse_csv(response)
        header = rows[0]
        data_row = rows[1]
        total_idx = header.index("total_score")
        # Both criteria scored 1 (first level)
        self.assertEqual(data_row[total_idx], "2")


# --- Assignment model method tests ----------------------------------


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentModelMethodTests(AssignmentTestMixin, APITestCase):
    """Tests for Assignment model methods not exercised through views."""

    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.rubric = self.create_rubric(self.user)

    def test_check_grading_complete_skips_non_grading_status(self):
        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.DRAFT
        )
        assignment.check_grading_complete()
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.DRAFT)

    def test_check_review_complete_skips_non_review_status(self):
        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.GRADING
        )
        assignment.check_review_complete()
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.GRADING)

    def test_cancel_grading_with_no_task_id(self):
        """cancel_grading is a no-op when celery_task_id is empty."""
        assignment = self.create_assignment(self.user, self.rubric)
        assignment.celery_task_id = ""
        assignment.save()
        # Should not raise
        assignment.cancel_grading()

    @patch("instagrader.celery.app.control.revoke")
    def test_cancel_grading_revokes_task(self, mock_revoke):
        assignment = self.create_assignment(self.user, self.rubric)
        assignment.celery_task_id = "task-abc-123"
        assignment.save()

        assignment.cancel_grading()
        mock_revoke.assert_called_once_with("task-abc-123", terminate=True)

    def test_assignment_str(self):
        assignment = self.create_assignment(self.user, self.rubric, title="My Title")
        self.assertEqual(str(assignment), "My Title")

    def test_essay_str(self):
        assignment = self.create_assignment(self.user, self.rubric, title="Hw1")
        essay = self.create_essay(assignment, file_name="alice.pdf")
        self.assertEqual(str(essay), "alice.pdf - Hw1")


# --- Task edge case tests -------------------------------------------


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class FinalizeEssayBatchTests(AssignmentTestMixin, APITestCase):
    """Tests for finalize_essay_batch task."""

    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.rubric = self.create_rubric(self.user)

    def test_finalize_missing_assignment_does_not_raise(self):
        from assignments.tasks import finalize_essay_batch

        # Should log warning and return without raising
        finalize_essay_batch([], str(uuid.uuid4()))

    def test_finalize_transitions_assignment(self):
        from assignments.tasks import finalize_essay_batch

        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.GRADING
        )
        self.create_essay(assignment, status=Essay.Status.GRADED)
        finalize_essay_batch([], str(assignment.id))
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.Status.REVIEW)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class GradeEssayEdgeCaseTests(GradingTestHelperMixin, APITestCase):
    """Tests for grade_essay task edge cases."""

    def setUp(self):
        self.password = "TestPassword123!"
        user = self.create_user()
        rubric = self.create_rubric_with_criteria(user)
        self.assignment = self.create_assignment(
            user, rubric, status=Assignment.Status.GRADING
        )

    def test_grade_essay_skips_nonexistent_essay(self):
        from assignments.tasks import grade_essay

        # Should log warning and return without raising
        grade_essay(str(uuid.uuid4()))

    def test_grade_essay_skips_already_failed_with_reason(self):
        from assignments.tasks import grade_essay

        essay = self.create_essay(
            self.assignment,
            status=Essay.Status.FAILED,
            extracted_text="",
            failure_reason="Prior failure",
        )
        grade_essay(str(essay.id))
        essay.refresh_from_db()
        # Should not overwrite the existing failure reason
        self.assertEqual(essay.failure_reason, "Prior failure")
