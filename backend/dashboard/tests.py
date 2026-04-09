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


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class DashboardTests(BaseTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.other_rubric = self.create_rubric(self.other_user)
        self.url = reverse("dashboard")

    def test_requires_auth(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_state(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(
            data["essay_status_counts"],
            {
                "pending": 0,
                "processing": 0,
                "graded": 0,
                "reviewed": 0,
                "failed": 0,
            },
        )
        self.assertEqual(
            data["assignment_status_counts"],
            {"draft": 0, "grading": 0, "review": 0, "completed": 0},
        )
        self.assertEqual(data["recent_activity"], [])
        self.assertEqual(
            data["totals"],
            {"total_assignments": 0, "total_essays": 0},
        )
        self.assertEqual(
            data["score_distribution"],
            [
                {"range": "0-20", "count": 0},
                {"range": "21-40", "count": 0},
                {"range": "41-60", "count": 0},
                {"range": "61-80", "count": 0},
                {"range": "81-100", "count": 0},
            ],
        )
        self.assertEqual(data["active_assignments"], [])

    def test_essay_status_counts(self):
        assignment = self.create_assignment(self.user, self.rubric)
        self.create_essay(assignment, status=Essay.Status.PENDING)
        self.create_essay(assignment, status=Essay.Status.PENDING)
        self.create_essay(assignment, status=Essay.Status.GRADED)
        self.create_essay(assignment, status=Essay.Status.REVIEWED)
        self.create_essay(assignment, status=Essay.Status.FAILED)

        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(data["essay_status_counts"]["pending"], 2)
        self.assertEqual(data["essay_status_counts"]["graded"], 1)
        self.assertEqual(data["essay_status_counts"]["reviewed"], 1)
        self.assertEqual(data["essay_status_counts"]["failed"], 1)
        self.assertEqual(data["essay_status_counts"]["processing"], 0)

    def test_assignment_status_counts(self):
        self.create_assignment(self.user, self.rubric, status=Assignment.Status.DRAFT)
        self.create_assignment(self.user, self.rubric, status=Assignment.Status.DRAFT)
        self.create_assignment(self.user, self.rubric, status=Assignment.Status.GRADING)
        self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.COMPLETED
        )

        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(data["assignment_status_counts"]["draft"], 2)
        self.assertEqual(data["assignment_status_counts"]["grading"], 1)
        self.assertEqual(data["assignment_status_counts"]["review"], 0)
        self.assertEqual(data["assignment_status_counts"]["completed"], 1)

    def test_totals(self):
        a1 = self.create_assignment(self.user, self.rubric)
        a2 = self.create_assignment(self.user, self.rubric)
        self.create_essay(a1)
        self.create_essay(a1)
        self.create_essay(a2)

        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(data["totals"]["total_assignments"], 2)
        self.assertEqual(data["totals"]["total_essays"], 3)

    def test_only_returns_own_data(self):
        # Create data for the other user
        other_assignment = self.create_assignment(self.other_user, self.other_rubric)
        self.create_essay(other_assignment, status=Essay.Status.GRADED)

        # Create data for the authenticated user
        my_assignment = self.create_assignment(self.user, self.rubric)
        self.create_essay(my_assignment, status=Essay.Status.PENDING)

        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(data["totals"]["total_assignments"], 1)
        self.assertEqual(data["totals"]["total_essays"], 1)
        self.assertEqual(data["essay_status_counts"]["pending"], 1)
        self.assertEqual(data["essay_status_counts"]["graded"], 0)

    def test_recent_activity_includes_graded_essays(self):
        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.REVIEW
        )
        essay = self.create_essay(assignment, status=Essay.Status.GRADED)

        response = self.client.get(self.url)
        data = response.json()

        graded_items = [
            a for a in data["recent_activity"] if a["type"] == "essay_graded"
        ]
        self.assertEqual(len(graded_items), 1)
        self.assertEqual(graded_items[0]["essay_file_name"], essay.file_name)
        self.assertEqual(graded_items[0]["assignment_title"], assignment.title)

    def test_recent_activity_includes_reviewed_essays(self):
        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.REVIEW
        )
        essay = self.create_essay(assignment, status=Essay.Status.REVIEWED)
        GradingResult.objects.create(
            essay=essay,
            teacher_approved=True,
            approved_at=timezone.now(),
        )

        response = self.client.get(self.url)
        data = response.json()

        reviewed_items = [
            a for a in data["recent_activity"] if a["type"] == "essay_reviewed"
        ]
        self.assertEqual(len(reviewed_items), 1)
        self.assertEqual(reviewed_items[0]["essay_file_name"], essay.file_name)

    def test_recent_activity_includes_completed_assignments(self):
        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.COMPLETED
        )

        response = self.client.get(self.url)
        data = response.json()

        completed_items = [
            a for a in data["recent_activity"] if a["type"] == "assignment_completed"
        ]
        self.assertEqual(len(completed_items), 1)
        self.assertEqual(completed_items[0]["assignment_title"], assignment.title)
        self.assertIsNone(completed_items[0]["essay_id"])

    def test_recent_activity_includes_failed_essays(self):
        assignment = self.create_assignment(self.user, self.rubric)
        essay = self.create_essay(assignment, status=Essay.Status.FAILED)

        response = self.client.get(self.url)
        data = response.json()

        failed_items = [
            a for a in data["recent_activity"] if a["type"] == "essay_failed"
        ]
        self.assertEqual(len(failed_items), 1)
        self.assertEqual(failed_items[0]["essay_file_name"], essay.file_name)

    def test_recent_activity_sorted_by_timestamp_descending(self):
        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.COMPLETED
        )
        # Create essays with different statuses -- they'll have
        # slightly different updated_at timestamps
        self.create_essay(assignment, status=Essay.Status.GRADED)
        self.create_essay(assignment, status=Essay.Status.FAILED)

        response = self.client.get(self.url)
        data = response.json()

        timestamps = [a["timestamp"] for a in data["recent_activity"]]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_recent_activity_limited_to_10(self):
        assignment = self.create_assignment(self.user, self.rubric)
        for _ in range(15):
            self.create_essay(assignment, status=Essay.Status.GRADED)

        response = self.client.get(self.url)
        data = response.json()

        self.assertLessEqual(len(data["recent_activity"]), 10)

    # --- Score distribution tests ---

    def _create_graded_essay_with_scores(
        self, assignment, criterion, levels, score_index
    ):
        """Helper: create a GRADED essay with a grading result at the given level."""
        essay = self.create_essay(assignment, status=Essay.Status.GRADED)
        result = GradingResult.objects.create(essay=essay)
        CriterionScore.objects.create(
            grading_result=result,
            criterion=criterion,
            level=levels[score_index],
            feedback="AI feedback",
        )
        return essay

    def test_score_distribution_buckets(self):
        criterion = RubricCriterion.objects.create(
            rubric=self.rubric, name="Quality", order=0
        )
        # Create levels: 0, 25, 50, 75, 100
        levels = []
        for score in [0, 25, 50, 75, 100]:
            levels.append(
                CriterionLevel.objects.create(
                    criterion=criterion,
                    score=score,
                    order=score,
                    descriptor=f"Score {score}",
                )
            )

        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.REVIEW
        )

        # Score 0/100 -> 0% -> bucket "0-20"
        self._create_graded_essay_with_scores(assignment, criterion, levels, 0)
        # Score 50/100 -> 50% -> bucket "41-60"
        self._create_graded_essay_with_scores(assignment, criterion, levels, 2)
        # Score 100/100 -> 100% -> bucket "81-100"
        self._create_graded_essay_with_scores(assignment, criterion, levels, 4)

        response = self.client.get(self.url)
        data = response.json()

        dist = {b["range"]: b["count"] for b in data["score_distribution"]}
        self.assertEqual(dist["0-20"], 1)
        self.assertEqual(dist["21-40"], 0)
        self.assertEqual(dist["41-60"], 1)
        self.assertEqual(dist["61-80"], 0)
        self.assertEqual(dist["81-100"], 1)

    def test_score_distribution_uses_teacher_override(self):
        criterion = RubricCriterion.objects.create(
            rubric=self.rubric, name="Quality", order=0
        )
        low = CriterionLevel.objects.create(
            criterion=criterion, score=10, order=0, descriptor="Low"
        )
        high = CriterionLevel.objects.create(
            criterion=criterion, score=100, order=1, descriptor="High"
        )

        assignment = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.REVIEW
        )
        essay = self.create_essay(assignment, status=Essay.Status.GRADED)
        result = GradingResult.objects.create(essay=essay)
        CriterionScore.objects.create(
            grading_result=result,
            criterion=criterion,
            level=low,  # AI gave 10/100
            teacher_level=high,  # Teacher overrode to 100/100
            feedback="AI feedback",
            teacher_review_state=CriterionScore.ReviewState.OVERRIDDEN,
        )

        response = self.client.get(self.url)
        data = response.json()

        dist = {b["range"]: b["count"] for b in data["score_distribution"]}
        # Teacher override (100/100 = 100%) should land in 81-100
        self.assertEqual(dist["81-100"], 1)
        self.assertEqual(dist["0-20"], 0)

    def test_score_distribution_excludes_other_users(self):
        criterion = RubricCriterion.objects.create(
            rubric=self.other_rubric, name="Quality", order=0
        )
        level = CriterionLevel.objects.create(
            criterion=criterion, score=50, order=0, descriptor="Mid"
        )

        other_assignment = self.create_assignment(
            self.other_user, self.other_rubric, status=Assignment.Status.REVIEW
        )
        essay = self.create_essay(other_assignment, status=Essay.Status.GRADED)
        result = GradingResult.objects.create(essay=essay)
        CriterionScore.objects.create(
            grading_result=result, criterion=criterion, level=level, feedback="f"
        )

        response = self.client.get(self.url)
        data = response.json()

        total = sum(b["count"] for b in data["score_distribution"])
        self.assertEqual(total, 0)

    # --- Active assignments tests ---

    def test_active_assignments_returns_grading_and_review(self):
        a1 = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.GRADING
        )
        a2 = self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.REVIEW
        )
        self.create_assignment(self.user, self.rubric, status=Assignment.Status.DRAFT)
        self.create_assignment(
            self.user, self.rubric, status=Assignment.Status.COMPLETED
        )

        self.create_essay(a1, status=Essay.Status.PROCESSING)
        self.create_essay(a1, status=Essay.Status.GRADED)
        self.create_essay(a2, status=Essay.Status.GRADED)
        self.create_essay(a2, status=Essay.Status.REVIEWED)

        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(len(data["active_assignments"]), 2)

        ids = {a["id"] for a in data["active_assignments"]}
        self.assertIn(str(a1.id), ids)
        self.assertIn(str(a2.id), ids)

        # Check a2's counts
        a2_data = next(a for a in data["active_assignments"] if a["id"] == str(a2.id))
        self.assertEqual(a2_data["total_essays"], 2)
        self.assertEqual(a2_data["reviewed_count"], 1)
        self.assertEqual(a2_data["graded_count"], 1)
        self.assertEqual(a2_data["failed_count"], 0)

    def test_active_assignments_excludes_other_users(self):
        self.create_assignment(
            self.other_user,
            self.other_rubric,
            status=Assignment.Status.GRADING,
        )

        response = self.client.get(self.url)
        data = response.json()

        self.assertEqual(len(data["active_assignments"]), 0)

    def test_active_assignments_limited_to_3(self):
        for _ in range(5):
            self.create_assignment(
                self.user, self.rubric, status=Assignment.Status.GRADING
            )

        response = self.client.get(self.url)
        data = response.json()

        self.assertLessEqual(len(data["active_assignments"]), 3)
