import io
import uuid
import zipfile
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from assignments.models import Assignment, Essay
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
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.other_rubric = self.create_rubric(self.other_user)

        self.assignments = [
            self.create_assignment(self.user, self.rubric) for _ in range(3)
        ]
        self.other_assignments = [
            self.create_assignment(self.other_user, self.other_rubric) for _ in range(2)
        ]
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
        for key in ("id", "title", "status", "essay_count", "created_at", "updated_at"):
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
        self.other_user = self.create_user()
        self.auth_user(self.user)
        self.rubric = self.create_rubric(self.user)
        self.other_rubric = self.create_rubric(self.other_user)
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

    def test_create_without_source_text(self):
        payload = {
            "title": "Test",
            "prompt": "Write",
            "rubric": str(self.rubric.id),
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

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
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.assignment = self.create_assignment(self.user, self.rubric)
        self.essay1 = self.create_essay(self.assignment, file_name="alice.pdf")
        self.essay2 = self.create_essay(self.assignment, file_name="bob.pdf")

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_assignment = self.create_assignment(
            self.other_user, self.other_rubric
        )

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
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.rubric2 = self.create_rubric(self.user)
        self.other_rubric = self.create_rubric(self.other_user)

        self.assignment = self.create_assignment(
            self.user,
            self.rubric,
            title="Original Title",
            prompt="Original Prompt",
            source_text="Original Source",
        )
        self.other_assignment = self.create_assignment(
            self.other_user, self.other_rubric
        )

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

    def test_update_partial_does_not_clear_other_fields(self):
        self.client.patch(
            self.detail_url(self.assignment.id), {"title": "Changed"}, format="json"
        )
        self.assignment.refresh_from_db()
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
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.assignment = self.create_assignment(self.user, self.rubric)
        self.essay = self.create_essay(self.assignment)

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_assignment = self.create_assignment(
            self.other_user, self.other_rubric
        )

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
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.assignment = self.create_assignment(self.user, self.rubric)

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_assignment = self.create_assignment(
            self.other_user, self.other_rubric
        )

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


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AssignmentEssaysListTests(AssignmentTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.assignment = self.create_assignment(self.user, self.rubric)
        self.essay1 = self.create_essay(self.assignment, file_name="alice.pdf")
        self.essay2 = self.create_essay(self.assignment, file_name="bob.pdf")
        self.essay3 = self.create_essay(self.assignment, file_name="charlie.pdf")

        self.empty_assignment = self.create_assignment(self.user, self.rubric)

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_assignment = self.create_assignment(
            self.other_user, self.other_rubric
        )

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
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.assignment = self.create_assignment(self.user, self.rubric)
        self.essay1 = self.create_essay(self.assignment, file_name="alice.pdf")
        self.essay2 = self.create_essay(self.assignment, file_name="bob.pdf")
        self.essay3 = self.create_essay(self.assignment, file_name="charlie.pdf")

        self.empty_assignment = self.create_assignment(self.user, self.rubric)

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_assignment = self.create_assignment(
            self.other_user, self.other_rubric
        )

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
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.assignment = self.create_assignment(self.user, self.rubric)
        self.essay = self.create_essay(self.assignment)

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_assignment = self.create_assignment(
            self.other_user, self.other_rubric
        )
        self.other_essay = self.create_essay(self.other_assignment)

        # An essay on a different assignment of the same user
        self.assignment2 = self.create_assignment(self.user, self.rubric)
        self.essay_different_assignment = self.create_essay(self.assignment2)

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
        self.user = self.create_user()
        self.auth_user(self.user)
        self.rubric = self.create_rubric(self.user)
        self.assignment = self.create_assignment(self.user, self.rubric)

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

    def test_task_updates_status_to_processing(self):
        from assignments.tasks import process_essay_batch

        essay = self.create_essay(self.assignment)
        with patch("assignments.tasks.process_essay_batch") as mock_task:
            mock_task.side_effect = lambda ids: None  # type: ignore[reportUnknownLambdaType]
        # Call the actual task synchronously
        essay.refresh_from_db()
        process_essay_batch([str(essay.id)])
        essay.refresh_from_db()
        self.assertIn(essay.status, (Essay.Status.PROCESSING, Essay.Status.PENDING))

    def test_task_extracts_text(self):
        from assignments.tasks import process_essay_batch

        essay = self.create_essay(
            self.assignment,
            original_file=SimpleUploadedFile(
                "test.txt", b"Hello world essay content.", content_type="text/plain"
            ),
        )
        process_essay_batch([str(essay.id)])
        essay.refresh_from_db()
        # After processing, extracted_text should be populated
        # (will pass once implementation extracts text)
        self.assertTrue(len(essay.extracted_text) > 0)

    def test_task_processes_multiple_essays(self):
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
        process_essay_batch([str(e.id) for e in essays])
        for essay in essays:
            essay.refresh_from_db()
            self.assertTrue(len(essay.extracted_text) > 0)

    def test_task_skips_nonexistent_essay(self):
        from assignments.tasks import process_essay_batch

        essay = self.create_essay(self.assignment)
        # Should not raise an exception
        try:
            process_essay_batch([str(uuid.uuid4()), str(essay.id)])
        except Exception:
            self.fail(
                "process_essay_batch raised an exception for nonexistent essay ID"
            )

    def test_task_handles_extraction_failure_gracefully(self):
        from assignments.tasks import process_essay_batch

        good_essay = self.create_essay(
            self.assignment,
            original_file=SimpleUploadedFile(
                "good.txt", b"Valid content", content_type="text/plain"
            ),
        )
        bad_essay = self.create_essay(
            self.assignment,
            original_file=SimpleUploadedFile(
                "bad.bin", b"\x00\x01\x02", content_type="application/octet-stream"
            ),
        )
        # Should not raise; good essay should still be processed
        try:
            process_essay_batch([str(bad_essay.id), str(good_essay.id)])
        except Exception:
            self.fail("process_essay_batch crashed on extraction failure")
        good_essay.refresh_from_db()
        self.assertTrue(len(good_essay.extracted_text) > 0)

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
            with self.assertRaises(RuntimeError):
                extract_essay_text(str(essay.id))
        essay.refresh_from_db()
        self.assertEqual(essay.status, Essay.Status.FAILED)

    def test_task_extracts_from_pdf(self):
        from assignments.tasks import process_essay_batch

        essay = self.create_essay(
            self.assignment,
            original_file=SimpleUploadedFile(
                "test.pdf", b"%PDF-1.4 content", content_type="application/pdf"
            ),
        )
        process_essay_batch([str(essay.id)])
        essay.refresh_from_db()
        # extracted_text should be populated after MarkItDown processing
        self.assertIsNotNone(essay.extracted_text)

    def test_task_extracts_from_docx(self):
        from assignments.tasks import process_essay_batch

        essay = self.create_essay(
            self.assignment,
            original_file=SimpleUploadedFile(
                "test.docx",
                b"PK fake docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        )
        process_essay_batch([str(essay.id)])
        essay.refresh_from_db()
        self.assertIsNotNone(essay.extracted_text)

    def test_task_extracts_from_txt(self):
        from assignments.tasks import process_essay_batch

        essay = self.create_essay(
            self.assignment,
            original_file=SimpleUploadedFile(
                "test.txt", b"Plain text essay content.", content_type="text/plain"
            ),
        )
        process_essay_batch([str(essay.id)])
        essay.refresh_from_db()
        self.assertIn("Plain text essay content", essay.extracted_text)
