import io
import json
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from assignments.models import Assignment, Essay
from grading.bedrock import (
    PROBE_MAX_ATTEMPTS,
    CriterionScoreResult,
    ModelNotReadyError,
    ModelUnavailableError,
    build_model_id_mapping,
    build_prompt,
    build_rubric_json,
    call_bedrock,
    parse_model_response,
    wait_for_model,
)
from grading.models import CriterionScore, GradingResult
from rubrics.models import CriterionLevel, Rubric, RubricCriterion
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

    def create_rubric_with_criteria(self, user: Any) -> Rubric:
        """Create a rubric with 2 criteria, each having 3 levels."""
        rubric = self.create_rubric(user)
        c1 = RubricCriterion.objects.create(rubric=rubric, name="Thesis", order=0)
        CriterionLevel.objects.create(criterion=c1, score=1, descriptor="Weak thesis")
        CriterionLevel.objects.create(
            criterion=c1, score=2, descriptor="Adequate thesis"
        )
        CriterionLevel.objects.create(criterion=c1, score=3, descriptor="Strong thesis")

        c2 = RubricCriterion.objects.create(rubric=rubric, name="Evidence", order=1)
        CriterionLevel.objects.create(criterion=c2, score=1, descriptor="Weak evidence")
        CriterionLevel.objects.create(
            criterion=c2, score=2, descriptor="Adequate evidence"
        )
        CriterionLevel.objects.create(
            criterion=c2, score=3, descriptor="Strong evidence"
        )

        return rubric

    def create_grading_result(self, essay: Essay) -> GradingResult:
        return GradingResult.objects.create(essay=essay)

    def create_criterion_score(
        self,
        grading_result: GradingResult,
        criterion: RubricCriterion,
        level: CriterionLevel,
        feedback: str = "Good work.",
    ) -> CriterionScore:
        return CriterionScore.objects.create(
            grading_result=grading_result,
            criterion=criterion,
            level=level,
            feedback=feedback,
        )


# --- Bedrock module tests --------------------------------------------


class TestBuildPrompt(GradingTestMixin, TestCase):
    password = "TestPassword123!"

    def setUp(self):
        user = self.create_user()
        self.rubric = self.create_rubric_with_criteria(user)

    def test_xml_sections_present(self):
        criteria = self.rubric.criteria.prefetch_related("levels").all()
        model_id_mapping = build_model_id_mapping(criteria)
        rubric_json = build_rubric_json(model_id_mapping)
        prompt = build_prompt(
            writing_prompt="Write an essay.",
            source_text="Some source text.",
            rubric_json=rubric_json,
            essay_text="This is my essay.",
        )
        self.assertIn("<system>", prompt)
        self.assertIn("<writing_prompt>", prompt)
        self.assertIn("<rubric>", prompt)
        self.assertIn("<essay>", prompt)
        self.assertIn("<output_schema>", prompt)
        self.assertIn("<source_text>", prompt)

    def test_no_source_text_section_when_empty(self):
        criteria = self.rubric.criteria.prefetch_related("levels").all()
        model_id_mapping = build_model_id_mapping(criteria)
        rubric_json = build_rubric_json(model_id_mapping)
        prompt = build_prompt(
            writing_prompt="Write an essay.",
            source_text="",
            rubric_json=rubric_json,
            essay_text="This is my essay.",
        )
        self.assertNotIn("<source_text>", prompt)

    def test_rubric_json_contains_numeric_ids(self):
        criteria = self.rubric.criteria.prefetch_related("levels").all()
        model_id_mapping = build_model_id_mapping(criteria)
        rubric_json = build_rubric_json(model_id_mapping)
        parsed = json.loads(rubric_json)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["name"], "Thesis")
        self.assertEqual(len(parsed[0]["levels"]), 3)
        self.assertIsInstance(parsed[0]["id"], int)
        self.assertIsInstance(parsed[0]["levels"][0]["id"], int)

    def test_prompt_instructions_require_strict_numeric_output(self):
        criteria = self.rubric.criteria.prefetch_related("levels").all()
        model_id_mapping = build_model_id_mapping(criteria)
        rubric_json = build_rubric_json(model_id_mapping)
        prompt = build_prompt(
            writing_prompt="Write an essay.",
            source_text="",
            rubric_json=rubric_json,
            essay_text="This is my essay.",
        )
        self.assertIn("IDs must be integers copied exactly", prompt)
        self.assertIn('single top-level key "scores"', prompt)
        self.assertIn("Do not use UUID values", prompt)


class TestParseModelResponse(GradingTestMixin, TestCase):
    password = "TestPassword123!"

    def setUp(self):
        user = self.create_user()
        self.rubric = self.create_rubric_with_criteria(user)
        criteria = list(self.rubric.criteria.prefetch_related("levels").all())
        criterion1 = criteria[0]
        criterion2 = criteria[1]
        # Add an extra level to criterion2 so we can verify level IDs are
        # validated per criterion, not globally.
        CriterionLevel.objects.create(
            criterion=criterion2, score=4, descriptor="Excellent evidence"
        )

        fresh_criteria = list(self.rubric.criteria.prefetch_related("levels").all())
        self.model_id_mapping = build_model_id_mapping(fresh_criteria)
        criteria_ids = sorted(self.model_id_mapping.criterion_numeric_to_uuid.keys())
        self.criterion1_id = criteria_ids[0]
        self.criterion2_id = criteria_ids[1]
        self.level1_id = min(
            self.model_id_mapping.level_numeric_to_uuid_by_criterion[self.criterion1_id]
        )
        self.level2_id = min(
            self.model_id_mapping.level_numeric_to_uuid_by_criterion[self.criterion2_id]
        )

    def test_correct_numeric_parsing(self):
        response_json = json.dumps(
            {
                "scores": [
                    {
                        "criteria_id": self.criterion1_id,
                        "level_id": self.level1_id,
                        "feedback": "Good thesis.",
                    },
                    {
                        "criteria_id": self.criterion2_id,
                        "level_id": self.level2_id,
                        "feedback": "Great evidence.",
                    },
                ]
            }
        )
        results = parse_model_response(response_json, self.model_id_mapping)
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], CriterionScoreResult)
        self.assertEqual(
            results[0].criterion_uuid,
            self.model_id_mapping.criterion_numeric_to_uuid[self.criterion1_id],
        )
        self.assertEqual(
            results[0].level_uuid,
            self.model_id_mapping.level_numeric_to_uuid_by_criterion[
                self.criterion1_id
            ][self.level1_id],
        )
        self.assertEqual(results[0].feedback, "Good thesis.")

    def test_accepts_digit_string_ids(self):
        response_json = json.dumps(
            {
                "scores": [
                    {
                        "criteria_id": str(self.criterion1_id),
                        "level_id": str(self.level1_id),
                        "feedback": "Good thesis.",
                    },
                    {
                        "criteria_id": str(self.criterion2_id),
                        "level_id": str(self.level2_id),
                        "feedback": "Great evidence.",
                    },
                ]
            }
        )
        results = parse_model_response(response_json, self.model_id_mapping)
        self.assertEqual(len(results), 2)

    def test_rejects_top_level_list(self):
        response_json = json.dumps(
            [
                {
                    "criteria_id": self.criterion1_id,
                    "level_id": self.level1_id,
                    "feedback": "Bad.",
                }
            ]
        )
        with self.assertRaises(ValueError) as ctx:
            parse_model_response(response_json, self.model_id_mapping)
        self.assertIn("JSON object", str(ctx.exception))

    def test_missing_scores_list_raises(self):
        response_json = json.dumps({"not_scores": []})
        with self.assertRaises(ValueError) as ctx:
            parse_model_response(response_json, self.model_id_mapping)
        self.assertIn("missing 'scores' list", str(ctx.exception))

    def test_non_numeric_criteria_id_raises(self):
        response_json = json.dumps(
            {
                "scores": [
                    {
                        "criteria_id": "abc",
                        "level_id": self.level1_id,
                        "feedback": "Bad.",
                    },
                ]
            }
        )
        with self.assertRaises(ValueError) as ctx:
            parse_model_response(response_json, self.model_id_mapping)
        self.assertIn("criteria_id must be an integer", str(ctx.exception))

    def test_duplicate_criteria_id_raises(self):
        response_json = json.dumps(
            {
                "scores": [
                    {
                        "criteria_id": self.criterion1_id,
                        "level_id": self.level1_id,
                        "feedback": "Bad.",
                    },
                    {
                        "criteria_id": self.criterion1_id,
                        "level_id": self.level1_id,
                        "feedback": "Bad.",
                    },
                ]
            }
        )
        with self.assertRaises(ValueError) as ctx:
            parse_model_response(response_json, self.model_id_mapping)
        self.assertIn("Duplicate criteria_id", str(ctx.exception))

    def test_missing_criterion_score_raises(self):
        response_json = json.dumps(
            {
                "scores": [
                    {
                        "criteria_id": self.criterion1_id,
                        "level_id": self.level1_id,
                        "feedback": "Bad.",
                    }
                ]
            }
        )
        with self.assertRaises(ValueError) as ctx:
            parse_model_response(response_json, self.model_id_mapping)
        self.assertIn("missing scores for criteria_id", str(ctx.exception))

    def test_level_not_valid_for_criterion_raises(self):
        level_ids_for_second = self.model_id_mapping.level_numeric_to_uuid_by_criterion[
            self.criterion2_id
        ]
        invalid_level_for_first = max(level_ids_for_second.keys())
        self.assertGreater(
            invalid_level_for_first,
            max(
                self.model_id_mapping.level_numeric_to_uuid_by_criterion[
                    self.criterion1_id
                ].keys()
            ),
        )

        response_json = json.dumps(
            {
                "scores": [
                    {
                        "criteria_id": self.criterion1_id,
                        "level_id": invalid_level_for_first,
                        "feedback": "Bad.",
                    },
                    {
                        "criteria_id": self.criterion2_id,
                        "level_id": self.level2_id,
                        "feedback": "Good.",
                    },
                ]
            }
        )
        with self.assertRaises(ValueError) as ctx:
            parse_model_response(response_json, self.model_id_mapping)
        self.assertIn(
            f"Unknown level_id {invalid_level_for_first}"
            f" for criteria_id {self.criterion1_id}",
            str(ctx.exception),
        )


# --- Grading view tests ----------------------------------------------


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class EssayDetailTests(GradingTestMixin, APITestCase):
    password = "TestPassword123!"

    def setUp(self):
        user = self.create_user()
        other_user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric(user)
        assignment = self.create_assignment(user, rubric)
        self.essay = self.create_essay(
            assignment,
            file_name="alice_essay.pdf",
            extracted_text="This is the extracted essay text content.",
        )

        other_rubric = self.create_rubric(other_user)
        other_assignment = self.create_assignment(other_user, other_rubric)
        self.other_essay = self.create_essay(other_assignment)

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
    password = "TestPassword123!"

    def setUp(self):
        user = self.create_user()
        other_user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric(user)
        assignment = self.create_assignment(user, rubric)
        self.essay1 = self.create_essay(assignment, file_name="essay_one.pdf")
        self.essay2 = self.create_essay(assignment, file_name="essay_two.pdf")

        other_rubric = self.create_rubric(other_user)
        other_assignment = self.create_assignment(other_user, other_rubric)
        self.other_essay = self.create_essay(other_assignment)

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


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class EssayRetryTests(GradingTestMixin, APITestCase):
    password = "TestPassword123!"

    def setUp(self):
        user = self.create_user()
        other_user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric_with_criteria(user)
        self.assignment = self.create_assignment(
            user, rubric, status=Assignment.Status.REVIEW
        )
        self.failed_essay = self.create_essay(
            self.assignment,
            status=Essay.Status.FAILED,
            extracted_text="stale text",
            file_name="failed.pdf",
        )

        other_rubric = self.create_rubric(other_user)
        other_assignment = self.create_assignment(other_user, other_rubric)
        self.other_failed_essay = self.create_essay(
            other_assignment, status=Essay.Status.FAILED
        )

    def retry_url(self, essay_id: uuid.UUID | str) -> str:
        return reverse("essay_retry", kwargs={"essay_id": essay_id})

    def test_retry_requires_auth(self):
        self.client.credentials()
        response = self.client.post(self.retry_url(self.failed_essay.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_retry_success_requeues_failed_essay(self, mock_delay: MagicMock):
        mock_delay.return_value = MagicMock(id="task-123")
        response = self.client.post(self.retry_url(self.failed_essay.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.failed_essay.refresh_from_db()
        self.assignment.refresh_from_db()

        self.assertEqual(self.failed_essay.status, Essay.Status.PENDING)
        self.assertEqual(self.failed_essay.extracted_text, "")
        self.assertEqual(self.assignment.status, Assignment.Status.GRADING)
        self.assertEqual(self.assignment.celery_task_id, "task-123")
        self.assertIsNotNone(self.assignment.grading_started_at)
        self.assertIsNone(self.assignment.grading_completed_at)
        mock_delay.assert_called_once_with([str(self.failed_essay.id)])

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_retry_non_failed_status_is_allowed(self, mock_delay: MagicMock):
        mock_delay.return_value = MagicMock(id="task-456")
        graded_essay = self.create_essay(
            self.assignment,
            status=Essay.Status.GRADED,
            extracted_text="old extracted text",
        )
        stale_result = self.create_grading_result(graded_essay)

        response = self.client.post(self.retry_url(graded_essay.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        graded_essay.refresh_from_db()
        self.assignment.refresh_from_db()
        self.assertEqual(graded_essay.status, Essay.Status.PENDING)
        self.assertEqual(graded_essay.extracted_text, "")
        self.assertEqual(graded_essay.failure_reason, "")
        self.assertFalse(GradingResult.objects.filter(id=stale_result.id).exists())
        self.assertEqual(self.assignment.status, Assignment.Status.GRADING)
        self.assertEqual(self.assignment.celery_task_id, "task-456")
        self.assertIsNotNone(self.assignment.grading_started_at)
        self.assertIsNone(self.assignment.grading_completed_at)
        mock_delay.assert_called_once_with([str(graded_essay.id)])

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_retry_other_user_essay_returns_404(self, mock_delay: MagicMock):
        response = self.client.post(self.retry_url(self.other_failed_essay.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_delay.assert_not_called()

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_retry_deletes_stale_grading_result(self, mock_delay: MagicMock):
        mock_delay.return_value = MagicMock(id="task-123")
        stale_result = self.create_grading_result(self.failed_essay)

        response = self.client.post(self.retry_url(self.failed_essay.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(GradingResult.objects.filter(id=stale_result.id).exists())

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_retry_while_grading_does_not_reset_started_at(self, mock_delay: MagicMock):
        mock_delay.return_value = MagicMock(id="task-789")
        initial_started_at = timezone.now()
        self.assignment.status = Assignment.Status.GRADING
        self.assignment.grading_started_at = initial_started_at
        self.assignment.grading_completed_at = None
        self.assignment.save(
            update_fields=["status", "grading_started_at", "grading_completed_at"]
        )

        response = self.client.post(self.retry_url(self.failed_essay.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.grading_started_at, initial_started_at)

    @patch("assignments.tasks.process_essay_batch.delay")
    def test_retry_after_completion_starts_new_timer(self, mock_delay: MagicMock):
        mock_delay.return_value = MagicMock(id="task-790")
        old_completed_at = timezone.now()
        self.assignment.status = Assignment.Status.COMPLETED
        self.assignment.grading_started_at = None
        self.assignment.grading_completed_at = old_completed_at
        self.assignment.save(
            update_fields=["status", "grading_started_at", "grading_completed_at"]
        )

        response = self.client.post(self.retry_url(self.failed_essay.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.Status.GRADING)
        self.assertIsNotNone(self.assignment.grading_started_at)
        self.assertIsNone(self.assignment.grading_completed_at)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class EssayGradingGetTests(GradingTestMixin, APITestCase):
    password = "TestPassword123!"

    def setUp(self):
        user = self.create_user()
        other_user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric_with_criteria(user)
        self.assignment = self.create_assignment(user, rubric)
        self.essay = self.create_essay(self.assignment, status=Essay.Status.GRADED)

        criteria = list(rubric.criteria.prefetch_related("levels").all())
        criterion1 = criteria[0]
        criterion2 = criteria[1]
        level1 = criterion1.levels.first()
        level2 = criterion2.levels.first()

        grading_result = self.create_grading_result(self.essay)
        self.create_criterion_score(grading_result, criterion1, level1)
        self.create_criterion_score(grading_result, criterion2, level2)

        other_rubric = self.create_rubric(other_user)
        other_assignment = self.create_assignment(other_user, other_rubric)
        self.other_essay = self.create_essay(other_assignment)

    def grading_url(self, essay_id: uuid.UUID | str) -> str:
        return reverse("essay_grading", kwargs={"essay_id": essay_id})

    def test_get_success(self):
        response = self.client.get(self.grading_url(self.essay.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("criterion_scores", response.data)
        self.assertEqual(len(response.data["criterion_scores"]), 2)

    def test_get_requires_auth(self):
        self.client.credentials()
        response = self.client.get(self.grading_url(self.essay.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_404_when_no_grading_result(self):
        essay_no_grade = self.create_essay(self.assignment)
        response = self.client.get(self.grading_url(essay_no_grade.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_other_user_returns_404(self):
        response = self.client.get(self.grading_url(self.other_essay.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_response_structure(self):
        response = self.client.get(self.grading_url(self.essay.id))
        for key in ("id", "essay", "teacher_approved", "criterion_scores"):
            self.assertIn(key, response.data)
        score_data = response.data["criterion_scores"][0]
        for key in (
            "id",
            "criterion",
            "level",
            "feedback",
            "teacher_review_state",
            "teacher_reviewed_at",
        ):
            self.assertIn(key, score_data)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class EssayGradingApproveTests(GradingTestMixin, APITestCase):
    password = "TestPassword123!"

    def setUp(self):
        user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric_with_criteria(user)
        self.assignment = self.create_assignment(
            user, rubric, status=Assignment.Status.REVIEW
        )
        self.essay = self.create_essay(self.assignment, status=Essay.Status.GRADED)

        criteria = list(rubric.criteria.prefetch_related("levels").all())
        criterion1 = criteria[0]
        self.level1 = criterion1.levels.first()

        self.grading_result = self.create_grading_result(self.essay)
        self.create_criterion_score(self.grading_result, criterion1, self.level1)

    def approve_url(self, essay_id: uuid.UUID | str) -> str:
        return reverse("essay_grading_approve", kwargs={"essay_id": essay_id})

    def test_approve_success(self):
        score = self.grading_result.criterion_scores.first()
        response = self.client.post(
            self.approve_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(score.id),
                        "teacher_review_state": "accepted_ai",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.grading_result.refresh_from_db()
        self.assertTrue(self.grading_result.teacher_approved)
        self.assertIsNotNone(self.grading_result.approved_at)

    def test_approve_transitions_essay_to_reviewed(self):
        score = self.grading_result.criterion_scores.first()
        self.client.post(
            self.approve_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(score.id),
                        "teacher_review_state": "accepted_ai",
                    }
                ]
            },
            format="json",
        )
        self.essay.refresh_from_db()
        self.assertEqual(self.essay.status, Essay.Status.REVIEWED)

    def test_approve_already_approved_returns_400(self):
        score = self.grading_result.criterion_scores.first()
        self.client.post(
            self.approve_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(score.id),
                        "teacher_review_state": "accepted_ai",
                    }
                ]
            },
            format="json",
        )
        response = self.client.post(
            self.approve_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(score.id),
                        "teacher_review_state": "accepted_ai",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_requires_auth(self):
        self.client.credentials()
        response = self.client.post(self.approve_url(self.essay.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_approve_404_when_no_grading_result(self):
        essay_no_grade = self.create_essay(self.assignment)
        response = self.client.post(self.approve_url(essay_no_grade.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_approve_triggers_review_complete(self):
        """When all essays are reviewed, assignment transitions to COMPLETED."""
        score = self.grading_result.criterion_scores.first()
        self.client.post(
            self.approve_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(score.id),
                        "teacher_review_state": "accepted_ai",
                    }
                ]
            },
            format="json",
        )
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, Assignment.Status.COMPLETED)

    def test_approve_rejects_when_any_criterion_pending(self):
        response = self.client.post(self.approve_url(self.essay.id), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.grading_result.refresh_from_db()
        self.assertFalse(self.grading_result.teacher_approved)

    def test_approve_applies_atomic_override_updates(self):
        score = self.grading_result.criterion_scores.first()
        response = self.client.post(
            self.approve_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(score.id),
                        "teacher_review_state": "overridden",
                        "teacher_level": str(self.level1.id),
                        "teacher_feedback": "Teacher override rationale",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        score.refresh_from_db()
        self.assertEqual(
            score.teacher_review_state,
            CriterionScore.ReviewState.OVERRIDDEN,
        )
        self.assertEqual(score.teacher_level_id, self.level1.id)
        self.assertEqual(score.teacher_feedback, "Teacher override rationale")

    def test_approve_update_payload_is_atomic_on_failure(self):
        score = self.grading_result.criterion_scores.first()
        response = self.client.post(
            self.approve_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(score.id),
                        "teacher_review_state": "accepted_ai",
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "teacher_review_state": "accepted_ai",
                    },
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        score.refresh_from_db()
        self.assertEqual(
            score.teacher_review_state,
            CriterionScore.ReviewState.PENDING,
        )
        self.grading_result.refresh_from_db()
        self.assertFalse(self.grading_result.teacher_approved)


# --- Bedrock retry/backoff tests -------------------------------------


def _make_model_not_ready_error() -> ClientError:
    """Build a ClientError with code ModelNotReadyException."""
    return ClientError(
        {"Error": {"Code": "ModelNotReadyException", "Message": "Model not ready"}},
        "InvokeModel",
    )


def _make_model_error() -> ClientError:
    """Build a ClientError with code ModelErrorException."""
    return ClientError(
        {
            "Error": {
                "Code": "ModelErrorException",
                "Message": "The request failed in the model container.",
            }
        },
        "InvokeModel",
    )


def _make_other_client_error() -> ClientError:
    """Build a non-retry ClientError (e.g., AccessDeniedException)."""
    return ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "Forbidden"}},
        "InvokeModel",
    )


def _make_success_response(content: str = "Hello") -> dict:
    """Build a fake Bedrock invoke_model response (Anthropic format)."""
    body = json.dumps({"content": [{"type": "text", "text": content}]})
    return {"body": io.BytesIO(body.encode())}


def _make_openai_success_response(content: str = "Hello") -> dict:
    """Build a fake Bedrock invoke_model response (OpenAI-compatible format)."""
    body = json.dumps({"choices": [{"message": {"content": content}}]})
    return {"body": io.BytesIO(body.encode())}


@patch("grading.bedrock.time.sleep", return_value=None)
@patch("grading.bedrock.boto3.client")
class TestCallBedrockRetry(TestCase):
    def test_succeeds_after_retries(self, mock_boto_client, mock_sleep):
        """Model not ready twice, succeeds on third attempt."""
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        mock_runtime.invoke_model.side_effect = [
            _make_model_not_ready_error(),
            _make_model_not_ready_error(),
            _make_success_response("Graded output"),
        ]

        result = call_bedrock("test prompt")

        self.assertEqual(result, "Graded output")
        self.assertEqual(mock_runtime.invoke_model.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(60)

    def test_raises_after_all_retries_exhausted(self, mock_boto_client, mock_sleep):
        """All 5 retries fail -> raises ModelNotReadyError."""
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        mock_runtime.invoke_model.side_effect = _make_model_not_ready_error()

        with self.assertRaises(ModelNotReadyError):
            call_bedrock("test prompt")

        self.assertEqual(mock_runtime.invoke_model.call_count, 5)
        self.assertEqual(mock_sleep.call_count, 4)

    def test_non_retry_error_propagates_immediately(self, mock_boto_client, mock_sleep):
        """Non-ModelNotReadyException ClientError raises immediately, no sleep."""
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        mock_runtime.invoke_model.side_effect = _make_other_client_error()

        with self.assertRaises(ClientError) as ctx:
            call_bedrock("test prompt")

        self.assertEqual(
            ctx.exception.response["Error"]["Code"], "AccessDeniedException"
        )
        self.assertEqual(mock_runtime.invoke_model.call_count, 1)
        mock_sleep.assert_not_called()


@patch("grading.bedrock.time.sleep", return_value=None)
@patch("grading.bedrock.boto3.client")
class TestWaitForModel(TestCase):
    def test_model_ready_immediately(self, mock_boto_client, mock_sleep):
        """Model responds on first probe -- returns silently."""
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        mock_runtime.invoke_model.return_value = _make_success_response()

        wait_for_model()  # Should not raise

        self.assertEqual(mock_runtime.invoke_model.call_count, 1)
        mock_sleep.assert_not_called()

    def test_ready_after_retries(self, mock_boto_client, mock_sleep):
        """Not ready twice, then ready on third probe."""
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        mock_runtime.invoke_model.side_effect = [
            _make_model_not_ready_error(),
            _make_model_not_ready_error(),
            _make_success_response(),
        ]

        wait_for_model()  # Should not raise

        self.assertEqual(mock_runtime.invoke_model.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_ready_after_model_error_retries(self, mock_boto_client, mock_sleep):
        """ModelErrorException is retried and can recover within probe window."""
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        mock_runtime.invoke_model.side_effect = [
            _make_model_error(),
            _make_model_error(),
            _make_success_response(),
        ]

        wait_for_model()  # Should not raise

        self.assertEqual(mock_runtime.invoke_model.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_raises_after_all_retries_exhausted(self, mock_boto_client, mock_sleep):
        """All not-ready probes fail -> raises ModelUnavailableError."""
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        mock_runtime.invoke_model.side_effect = _make_model_not_ready_error()

        with self.assertRaises(ModelUnavailableError) as ctx:
            wait_for_model()

        self.assertIn("ModelNotReadyException", str(ctx.exception))
        self.assertEqual(mock_runtime.invoke_model.call_count, PROBE_MAX_ATTEMPTS)
        self.assertEqual(mock_sleep.call_count, PROBE_MAX_ATTEMPTS - 1)

    def test_raises_after_model_error_retries_exhausted(
        self, mock_boto_client, mock_sleep
    ):
        """All model-error probes fail -> ModelUnavailableError."""
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        mock_runtime.invoke_model.side_effect = _make_model_error()

        with self.assertRaises(ModelUnavailableError) as ctx:
            wait_for_model()

        self.assertIn("ModelErrorException", str(ctx.exception))
        self.assertIn("model container", str(ctx.exception))
        self.assertEqual(mock_runtime.invoke_model.call_count, PROBE_MAX_ATTEMPTS)
        self.assertEqual(mock_sleep.call_count, PROBE_MAX_ATTEMPTS - 1)


# --- EssayGradingView.patch() tests ---------------------------------


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class EssayGradingSaveTests(GradingTestMixin, APITestCase):
    """Tests for PATCH /api/essays/<id>/grading/ (save without approve)."""

    password = "TestPassword123!"

    def setUp(self):
        user = self.create_user()
        other_user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric_with_criteria(user)
        self.assignment = self.create_assignment(
            user, rubric, status=Assignment.Status.REVIEW
        )
        self.essay = self.create_essay(self.assignment, status=Essay.Status.GRADED)

        criteria = list(rubric.criteria.prefetch_related("levels").all())
        criterion1 = criteria[0]
        criterion2 = criteria[1]
        self.level1 = criterion1.levels.first()
        level2 = criterion2.levels.first()
        self.level1_alt = criterion1.levels.last()

        self.grading_result = self.create_grading_result(self.essay)
        self.score1 = self.create_criterion_score(
            self.grading_result, criterion1, self.level1
        )
        self.create_criterion_score(self.grading_result, criterion2, level2)

        other_rubric = self.create_rubric(other_user)
        other_assignment = self.create_assignment(other_user, other_rubric)
        self.other_essay = self.create_essay(other_assignment)

    def grading_url(self, essay_id):
        return reverse("essay_grading", kwargs={"essay_id": essay_id})

    def test_patch_requires_auth(self):
        self.client.credentials()
        response = self.client.patch(self.grading_url(self.essay.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_save_accepted_ai(self):
        response = self.client.patch(
            self.grading_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(self.score1.id),
                        "teacher_review_state": "accepted_ai",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.score1.refresh_from_db()
        self.assertEqual(
            self.score1.teacher_review_state, CriterionScore.ReviewState.ACCEPTED_AI
        )
        self.assertIsNone(self.score1.teacher_level)
        self.assertIsNotNone(self.score1.teacher_reviewed_at)

    def test_patch_save_overridden(self):
        response = self.client.patch(
            self.grading_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(self.score1.id),
                        "teacher_review_state": "overridden",
                        "teacher_level": str(self.level1_alt.id),
                        "teacher_feedback": "Better answer",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.score1.refresh_from_db()
        self.assertEqual(
            self.score1.teacher_review_state, CriterionScore.ReviewState.OVERRIDDEN
        )
        self.assertEqual(self.score1.teacher_level_id, self.level1_alt.id)
        self.assertEqual(self.score1.teacher_feedback, "Better answer")

    def test_patch_does_not_approve(self):
        """PATCH saves but does not set teacher_approved."""
        self.client.patch(
            self.grading_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(self.score1.id),
                        "teacher_review_state": "accepted_ai",
                    }
                ]
            },
            format="json",
        )
        self.grading_result.refresh_from_db()
        self.assertFalse(self.grading_result.teacher_approved)

    def test_patch_empty_payload(self):
        response = self.client.patch(self.grading_url(self.essay.id), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patch_other_user_returns_404(self):
        response = self.client.patch(
            self.grading_url(self.other_essay.id),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_no_grading_result_returns_404(self):
        essay_no_grade = self.create_essay(self.assignment)
        response = self.client.patch(
            self.grading_url(essay_no_grade.id), {}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_overridden_without_teacher_level_returns_400(self):
        response = self.client.patch(
            self.grading_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(self.score1.id),
                        "teacher_review_state": "overridden",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("teacher_level is required", response.data["detail"])

    def test_patch_accepted_ai_with_teacher_level_returns_400(self):
        response = self.client.patch(
            self.grading_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(self.score1.id),
                        "teacher_review_state": "accepted_ai",
                        "teacher_level": str(self.level1.id),
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("teacher_level must be null", response.data["detail"])

    def test_patch_unknown_criterion_score_returns_404(self):
        response = self.client.patch(
            self.grading_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(uuid.uuid4()),
                        "teacher_review_state": "accepted_ai",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_backward_compat_teacher_level_only(self):
        """Old clients sending teacher_level without review_state infers OVERRIDDEN."""
        response = self.client.patch(
            self.grading_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(self.score1.id),
                        "teacher_level": str(self.level1_alt.id),
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.score1.refresh_from_db()
        self.assertEqual(
            self.score1.teacher_review_state, CriterionScore.ReviewState.OVERRIDDEN
        )

    def test_patch_backward_compat_null_teacher_level_infers_accepted_ai(self):
        """Old clients sending teacher_level=null infers ACCEPTED_AI."""
        response = self.client.patch(
            self.grading_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(self.score1.id),
                        "teacher_level": None,
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.score1.refresh_from_db()
        self.assertEqual(
            self.score1.teacher_review_state, CriterionScore.ReviewState.ACCEPTED_AI
        )
        self.assertIsNone(self.score1.teacher_level)

    def test_patch_accepted_ai_normalizes_teacher_level_to_null(self):
        """Setting accepted_ai clears any existing teacher_level."""
        self.score1.teacher_level = self.level1_alt
        self.score1.teacher_review_state = CriterionScore.ReviewState.OVERRIDDEN
        self.score1.save()

        response = self.client.patch(
            self.grading_url(self.essay.id),
            {
                "criterion_scores": [
                    {
                        "id": str(self.score1.id),
                        "teacher_review_state": "accepted_ai",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.score1.refresh_from_db()
        self.assertIsNone(self.score1.teacher_level)


# --- EssayRetryView additional tests --------------------------------


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class EssayRetryPendingProcessingTests(GradingTestMixin, APITestCase):
    """Test retry rejects essays that are already pending or processing."""

    password = "TestPassword123!"

    def setUp(self):
        user = self.create_user()
        self.auth_user(user)

        rubric = self.create_rubric_with_criteria(user)
        self.assignment = self.create_assignment(
            user, rubric, status=Assignment.Status.GRADING
        )

    def retry_url(self, essay_id):
        return reverse("essay_retry", kwargs={"essay_id": essay_id})

    def test_retry_pending_essay_returns_400(self):
        essay = self.create_essay(self.assignment, status=Essay.Status.PENDING)
        response = self.client.post(self.retry_url(essay.id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already pending or processing", response.data["detail"])

    def test_retry_processing_essay_returns_400(self):
        essay = self.create_essay(self.assignment, status=Essay.Status.PROCESSING)
        response = self.client.post(self.retry_url(essay.id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# --- Non-Anthropic (OpenAI-compatible) Bedrock path -----------------


NON_ANTHROPIC_BEDROCK = {
    "MODEL_ID": "arn:aws:bedrock:us-east-1:1234:imported-model/gpt-oss-20b",
    "REGION": "us-east-1",
    "MAX_COMPLETION_TOKENS": 4096,
    "TEMPERATURE": 0.0,
}


@override_settings(BEDROCK=NON_ANTHROPIC_BEDROCK)
@patch("grading.bedrock.time.sleep", return_value=None)
@patch("grading.bedrock.boto3.client")
class TestCallBedrockNonAnthropic(TestCase):
    """Test OpenAI-compatible (non-Anthropic) model path in call_bedrock."""

    def test_openai_format_response_parsed(self, mock_boto_client, mock_sleep):
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        mock_runtime.invoke_model.return_value = _make_openai_success_response(
            "Graded output"
        )

        result = call_bedrock("test prompt")
        self.assertEqual(result, "Graded output")

    def test_openai_reasoning_content_fallback(self, mock_boto_client, mock_sleep):
        """When content is empty, falls back to reasoning_content."""
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        body = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "reasoning_content": "Reasoned output",
                        }
                    }
                ]
            }
        )
        mock_runtime.invoke_model.return_value = {"body": io.BytesIO(body.encode())}

        result = call_bedrock("test prompt")
        self.assertEqual(result, "Reasoned output")

    def test_openai_empty_response_raises(self, mock_boto_client, mock_sleep):
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        body = json.dumps(
            {"choices": [{"message": {"content": "", "reasoning_content": ""}}]}
        )
        mock_runtime.invoke_model.return_value = {"body": io.BytesIO(body.encode())}

        with self.assertRaises(ValueError) as ctx:
            call_bedrock("test prompt")
        self.assertIn("empty response", str(ctx.exception))

    def test_openai_request_uses_max_completion_tokens(
        self, mock_boto_client, mock_sleep
    ):
        """Non-Anthropic models use max_completion_tokens, not max_tokens."""
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        mock_runtime.invoke_model.return_value = _make_openai_success_response("ok")

        call_bedrock("test prompt")

        call_args = json.loads(mock_runtime.invoke_model.call_args[1]["body"])
        self.assertIn("max_completion_tokens", call_args)
        self.assertNotIn("max_tokens", call_args)
        self.assertNotIn("anthropic_version", call_args)


@override_settings(BEDROCK=NON_ANTHROPIC_BEDROCK)
@patch("grading.bedrock.time.sleep", return_value=None)
@patch("grading.bedrock.boto3.client")
class TestWaitForModelNonAnthropic(TestCase):
    """Test wait_for_model probe uses non-Anthropic format."""

    def test_probe_uses_max_completion_tokens(self, mock_boto_client, mock_sleep):
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        mock_runtime.invoke_model.return_value = _make_openai_success_response()

        wait_for_model()

        call_args = json.loads(mock_runtime.invoke_model.call_args[1]["body"])
        self.assertIn("max_completion_tokens", call_args)
        self.assertNotIn("anthropic_version", call_args)

    def test_non_retryable_error_propagates(self, mock_boto_client, mock_sleep):
        """Non-retryable errors (e.g. AccessDenied) raise immediately."""
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        mock_runtime.invoke_model.side_effect = _make_other_client_error()

        with self.assertRaises(ClientError) as ctx:
            wait_for_model()

        self.assertEqual(
            ctx.exception.response["Error"]["Code"], "AccessDeniedException"
        )
        self.assertEqual(mock_runtime.invoke_model.call_count, 1)
        mock_sleep.assert_not_called()


# --- parse_model_response edge cases --------------------------------


class TestParseModelResponseEdgeCases(GradingTestMixin, TestCase):
    password = "TestPassword123!"

    def setUp(self):
        user = self.create_user()
        rubric = self.create_rubric_with_criteria(user)
        criteria = list(rubric.criteria.prefetch_related("levels").all())
        self.model_id_mapping = build_model_id_mapping(criteria)
        criteria_ids = sorted(self.model_id_mapping.criterion_numeric_to_uuid.keys())
        self.c1_id = criteria_ids[0]
        self.c2_id = criteria_ids[1]
        self.l1_id = min(
            self.model_id_mapping.level_numeric_to_uuid_by_criterion[self.c1_id]
        )
        self.l2_id = min(
            self.model_id_mapping.level_numeric_to_uuid_by_criterion[self.c2_id]
        )

    def test_boolean_criteria_id_raises(self):
        response_json = json.dumps(
            {
                "scores": [
                    {"criteria_id": True, "level_id": self.l1_id, "feedback": "X"},
                ]
            }
        )
        with self.assertRaises(ValueError) as ctx:
            parse_model_response(response_json, self.model_id_mapping)
        self.assertIn("must be an integer", str(ctx.exception))

    def test_missing_feedback_raises(self):
        response_json = json.dumps(
            {
                "scores": [
                    {
                        "criteria_id": self.c1_id,
                        "level_id": self.l1_id,
                        "feedback": "",
                    },
                    {
                        "criteria_id": self.c2_id,
                        "level_id": self.l2_id,
                        "feedback": "Ok",
                    },
                ]
            }
        )
        with self.assertRaises(ValueError) as ctx:
            parse_model_response(response_json, self.model_id_mapping)
        self.assertIn("Missing feedback", str(ctx.exception))

    def test_unknown_criteria_id_raises(self):
        response_json = json.dumps(
            {
                "scores": [
                    {"criteria_id": 999, "level_id": self.l1_id, "feedback": "X"},
                ]
            }
        )
        with self.assertRaises(ValueError) as ctx:
            parse_model_response(response_json, self.model_id_mapping)
        self.assertIn("Unknown criteria_id", str(ctx.exception))

    def test_non_dict_score_entry_raises(self):
        response_json = json.dumps({"scores": ["not a dict"]})
        with self.assertRaises(ValueError) as ctx:
            parse_model_response(response_json, self.model_id_mapping)
        self.assertIn("must be an object", str(ctx.exception))
