import uuid
from typing import Any

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from assignments.models import Assignment
from rubrics.models import CriterionLevel, Rubric, RubricCriterion
from tests.helpers import BaseTestMixin, faker


class RubricTestMixin(BaseTestMixin):
    """Rubric-specific test helpers."""

    def create_criterion(self, rubric: Rubric, **kwargs: Any) -> RubricCriterion:
        defaults: dict[str, Any] = {"name": faker.word(), "order": 0}
        defaults.update(kwargs)
        return RubricCriterion.objects.create(rubric=rubric, **defaults)

    def create_level(self, criterion: RubricCriterion, **kwargs: Any) -> CriterionLevel:
        defaults: dict[str, Any] = {"score": 1, "descriptor": faker.sentence()}
        defaults.update(kwargs)
        return CriterionLevel.objects.create(criterion=criterion, **defaults)


class RubricListTests(RubricTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)
        self.rubrics = [self.create_rubric(self.user) for _ in range(3)]
        self.other_rubrics = [self.create_rubric(self.other_user) for _ in range(2)]
        self.url = reverse("rubric_list_create")

    def test_list_requires_auth(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_own_rubrics(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {r["id"] for r in response.data}
        own_ids = {str(r.id) for r in self.rubrics}
        self.assertEqual(returned_ids, own_ids)

    def test_list_response_uses_list_serializer(self):
        response = self.client.get(self.url)
        item = response.data[0]
        for key in ("id", "title", "description", "created_at", "updated_at"):
            self.assertIn(key, item)
        self.assertNotIn("criteria", item)

    def test_list_empty_for_new_user(self):
        new_user = self.create_user()
        self.auth_user(new_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_list_ordered_by_created_at_desc(self):
        response = self.client.get(self.url)
        dates = [r["created_at"] for r in response.data]
        self.assertEqual(dates, sorted(dates, reverse=True))


class RubricCreateTests(RubricTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.auth_user(self.user)
        self.url = reverse("rubric_list_create")

    def test_create_requires_auth(self):
        self.client.credentials()
        response = self.client.post(self.url, {"title": "Test"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_success(self):
        payload = {"title": "Essay Rubric", "description": "A rubric for essays"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        rubric = Rubric.objects.get(id=response.data["id"])
        self.assertEqual(rubric.user, self.user)
        self.assertEqual(rubric.title, payload["title"])

    def test_create_response_uses_detail_serializer(self):
        payload = {"title": "Essay Rubric"}
        response = self.client.post(self.url, payload, format="json")
        for key in (
            "id",
            "title",
            "description",
            "criteria",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, response.data)
        self.assertEqual(response.data["criteria"], [])

    def test_create_without_description(self):
        payload = {"title": "No Description Rubric"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_missing_title_returns_400(self):
        response = self.client.post(
            self.url, {"description": "No title"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_blank_title_returns_400(self):
        response = self.client.post(self.url, {"title": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_sets_user_from_request(self):
        other = self.create_user()
        payload = {"title": "Rubric", "user": str(other.id)}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        rubric = Rubric.objects.get(id=response.data["id"])
        self.assertEqual(rubric.user, self.user)


class RubricDetailTests(RubricTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        c1 = self.create_criterion(self.rubric, name="Thesis", order=0)
        c2 = self.create_criterion(self.rubric, name="Evidence", order=1)
        self.create_level(c1, score=1, descriptor="Weak")
        self.create_level(c1, score=2, descriptor="Strong")
        self.create_level(c2, score=1, descriptor="Missing")
        self.create_level(c2, score=2, descriptor="Present")

        self.other_rubric = self.create_rubric(self.other_user)

    def detail_url(self, rubric_id: uuid.UUID | str) -> str:
        return reverse("rubric_detail", kwargs={"rubric_id": rubric_id})

    def test_detail_requires_auth(self):
        self.client.credentials()
        response = self.client.get(self.detail_url(self.rubric.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_success(self):
        response = self.client.get(self.detail_url(self.rubric.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.rubric.title)

    def test_detail_includes_nested_criteria_and_levels(self):
        response = self.client.get(self.detail_url(self.rubric.id))
        criteria = response.data["criteria"]
        self.assertEqual(len(criteria), 2)
        for criterion in criteria:
            for key in ("id", "name", "order", "levels"):
                self.assertIn(key, criterion)
            for level in criterion["levels"]:
                for key in ("id", "score", "descriptor"):
                    self.assertIn(key, level)

    def test_detail_other_user_returns_404(self):
        response = self.client.get(self.detail_url(self.other_rubric.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_nonexistent_uuid_returns_404(self):
        response = self.client.get(self.detail_url(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RubricUpdateTests(RubricTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)
        self.rubric = self.create_rubric(
            self.user, title="Original", description="Desc"
        )
        self.other_rubric = self.create_rubric(self.other_user)

    def detail_url(self, rubric_id: uuid.UUID | str) -> str:
        return reverse("rubric_detail", kwargs={"rubric_id": rubric_id})

    def test_update_requires_auth(self):
        self.client.credentials()
        response = self.client.patch(
            self.detail_url(self.rubric.id), {"title": "New"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_title_success(self):
        response = self.client.patch(
            self.detail_url(self.rubric.id), {"title": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.rubric.refresh_from_db()
        self.assertEqual(self.rubric.title, "Updated")

    def test_update_description_success(self):
        response = self.client.patch(
            self.detail_url(self.rubric.id), {"description": "New desc"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.rubric.refresh_from_db()
        self.assertEqual(self.rubric.description, "New desc")

    def test_update_partial_does_not_clear_other_fields(self):
        self.client.patch(
            self.detail_url(self.rubric.id), {"title": "Changed"}, format="json"
        )
        self.rubric.refresh_from_db()
        self.assertEqual(self.rubric.description, "Desc")

    def test_update_other_user_returns_404(self):
        response = self.client.patch(
            self.detail_url(self.other_rubric.id), {"title": "Hack"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_nonexistent_uuid_returns_404(self):
        response = self.client.patch(
            self.detail_url(uuid.uuid4()), {"title": "Nope"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_blank_title_returns_400(self):
        response = self.client.patch(
            self.detail_url(self.rubric.id), {"title": ""}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RubricDeleteTests(RubricTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)
        self.rubric = self.create_rubric(self.user)
        self.other_rubric = self.create_rubric(self.other_user)

    def detail_url(self, rubric_id: uuid.UUID | str) -> str:
        return reverse("rubric_detail", kwargs={"rubric_id": rubric_id})

    def test_delete_requires_auth(self):
        self.client.credentials()
        response = self.client.delete(self.detail_url(self.rubric.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_success(self):
        response = self.client.delete(self.detail_url(self.rubric.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Rubric.objects.filter(id=self.rubric.id).exists())

    def test_delete_cascades_criteria_and_levels(self):
        criterion = self.create_criterion(self.rubric)
        self.create_level(criterion)
        rubric_id = self.rubric.id

        self.client.delete(self.detail_url(rubric_id))

        self.assertFalse(RubricCriterion.objects.filter(rubric_id=rubric_id).exists())
        self.assertFalse(
            CriterionLevel.objects.filter(criterion__rubric_id=rubric_id).exists()
        )

    def test_delete_other_user_returns_404(self):
        response = self.client.delete(self.detail_url(self.other_rubric.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_uuid_returns_404(self):
        response = self.client.delete(self.detail_url(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_rubric_in_use_by_assignment_blocked(self):
        Assignment.objects.create(
            user=self.user,
            rubric=self.rubric,
            title="Test Assignment",
            prompt="Write an essay",
        )
        response = self.client.delete(self.detail_url(self.rubric.id))
        self.assertIn(
            response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT),
        )
        self.assertTrue(Rubric.objects.filter(id=self.rubric.id).exists())


class CriterionCreateTests(RubricTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)
        self.rubric = self.create_rubric(self.user)
        self.other_rubric = self.create_rubric(self.other_user)

    def criteria_url(self, rubric_id: uuid.UUID | str) -> str:
        return reverse("criterion_list_create", kwargs={"rubric_id": rubric_id})

    def test_create_requires_auth(self):
        self.client.credentials()
        response = self.client.post(
            self.criteria_url(self.rubric.id), {"name": "Test"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_success(self):
        response = self.client.post(
            self.criteria_url(self.rubric.id), {"name": "Thesis"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        criterion = RubricCriterion.objects.get(id=response.data["id"])
        self.assertEqual(criterion.rubric, self.rubric)
        self.assertEqual(criterion.name, "Thesis")

    def test_create_response_keys(self):
        response = self.client.post(
            self.criteria_url(self.rubric.id), {"name": "Thesis"}, format="json"
        )
        for key in ("id", "name", "order", "levels"):
            self.assertIn(key, response.data)
        self.assertEqual(response.data["levels"], [])

    def test_create_default_order(self):
        response = self.client.post(
            self.criteria_url(self.rubric.id), {"name": "Thesis"}, format="json"
        )
        self.assertEqual(response.data["order"], 0)

    def test_create_explicit_order(self):
        response = self.client.post(
            self.criteria_url(self.rubric.id),
            {"name": "Thesis", "order": 5},
            format="json",
        )
        self.assertEqual(response.data["order"], 5)

    def test_create_missing_name_returns_400(self):
        response = self.client.post(
            self.criteria_url(self.rubric.id), {"order": 1}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_other_user_rubric_returns_404(self):
        response = self.client.post(
            self.criteria_url(self.other_rubric.id), {"name": "Hack"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_nonexistent_rubric_returns_404(self):
        response = self.client.post(
            self.criteria_url(uuid.uuid4()), {"name": "Nope"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CriterionUpdateTests(RubricTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.criterion = self.create_criterion(self.rubric, name="Thesis", order=0)
        self.rubric2 = self.create_rubric(self.user)
        self.criterion_other_rubric = self.create_criterion(
            self.rubric2, name="Evidence"
        )

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_criterion = self.create_criterion(self.other_rubric)

    def criterion_url(
        self, rubric_id: uuid.UUID | str, criterion_id: uuid.UUID | str
    ) -> str:
        return reverse(
            "criterion_detail",
            kwargs={"rubric_id": rubric_id, "criterion_id": criterion_id},
        )

    def test_update_requires_auth(self):
        self.client.credentials()
        response = self.client.patch(
            self.criterion_url(self.rubric.id, self.criterion.id),
            {"name": "New"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_name_success(self):
        response = self.client.patch(
            self.criterion_url(self.rubric.id, self.criterion.id),
            {"name": "Updated Thesis"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.criterion.refresh_from_db()
        self.assertEqual(self.criterion.name, "Updated Thesis")

    def test_update_order_success(self):
        response = self.client.patch(
            self.criterion_url(self.rubric.id, self.criterion.id),
            {"order": 10},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.criterion.refresh_from_db()
        self.assertEqual(self.criterion.order, 10)

    def test_update_other_user_rubric_returns_404(self):
        response = self.client.patch(
            self.criterion_url(self.other_rubric.id, self.other_criterion.id),
            {"name": "Hack"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_nonexistent_rubric_returns_404(self):
        response = self.client.patch(
            self.criterion_url(uuid.uuid4(), self.criterion.id),
            {"name": "Nope"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_nonexistent_criterion_returns_404(self):
        response = self.client.patch(
            self.criterion_url(self.rubric.id, uuid.uuid4()),
            {"name": "Nope"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_criterion_wrong_rubric_returns_404(self):
        response = self.client.patch(
            self.criterion_url(self.rubric.id, self.criterion_other_rubric.id),
            {"name": "Cross-rubric"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CriterionDeleteTests(RubricTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.criterion = self.create_criterion(self.rubric)
        self.level = self.create_level(self.criterion)

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_criterion = self.create_criterion(self.other_rubric)

    def criterion_url(
        self, rubric_id: uuid.UUID | str, criterion_id: uuid.UUID | str
    ) -> str:
        return reverse(
            "criterion_detail",
            kwargs={"rubric_id": rubric_id, "criterion_id": criterion_id},
        )

    def test_delete_requires_auth(self):
        self.client.credentials()
        response = self.client.delete(
            self.criterion_url(self.rubric.id, self.criterion.id)
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_success(self):
        response = self.client.delete(
            self.criterion_url(self.rubric.id, self.criterion.id)
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(RubricCriterion.objects.filter(id=self.criterion.id).exists())

    def test_delete_cascades_levels(self):
        level_id = self.level.id
        self.client.delete(self.criterion_url(self.rubric.id, self.criterion.id))
        self.assertFalse(CriterionLevel.objects.filter(id=level_id).exists())

    def test_delete_other_user_rubric_returns_404(self):
        response = self.client.delete(
            self.criterion_url(self.other_rubric.id, self.other_criterion.id)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_criterion_returns_404(self):
        response = self.client.delete(self.criterion_url(self.rubric.id, uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CriterionReorderTests(RubricTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.c1 = self.create_criterion(self.rubric, name="A", order=0)
        self.c2 = self.create_criterion(self.rubric, name="B", order=1)
        self.c3 = self.create_criterion(self.rubric, name="C", order=2)

        self.other_rubric = self.create_rubric(self.other_user)

    def reorder_url(self, rubric_id: uuid.UUID | str) -> str:
        return reverse("criterion_reorder", kwargs={"rubric_id": rubric_id})

    def test_reorder_requires_auth(self):
        self.client.credentials()
        response = self.client.post(
            self.reorder_url(self.rubric.id),
            {"order": [str(self.c3.id), str(self.c1.id), str(self.c2.id)]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reorder_success(self):
        new_order = [str(self.c3.id), str(self.c1.id), str(self.c2.id)]
        response = self.client.post(
            self.reorder_url(self.rubric.id), {"order": new_order}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.c1.refresh_from_db()
        self.c2.refresh_from_db()
        self.c3.refresh_from_db()
        self.assertEqual(self.c3.order, 0)
        self.assertEqual(self.c1.order, 1)
        self.assertEqual(self.c2.order, 2)

    def test_reorder_reflected_in_detail(self):
        new_order = [str(self.c3.id), str(self.c1.id), str(self.c2.id)]
        self.client.post(
            self.reorder_url(self.rubric.id), {"order": new_order}, format="json"
        )
        response = self.client.get(
            reverse("rubric_detail", kwargs={"rubric_id": self.rubric.id})
        )
        criteria_names = [c["name"] for c in response.data["criteria"]]
        self.assertEqual(criteria_names, ["C", "A", "B"])

    def test_reorder_other_user_rubric_returns_404(self):
        response = self.client.post(
            self.reorder_url(self.other_rubric.id),
            {"order": [str(uuid.uuid4())]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reorder_nonexistent_rubric_returns_404(self):
        response = self.client.post(
            self.reorder_url(uuid.uuid4()),
            {"order": [str(self.c1.id)]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reorder_incomplete_list_returns_400(self):
        response = self.client.post(
            self.reorder_url(self.rubric.id),
            {"order": [str(self.c1.id), str(self.c2.id)]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_extra_ids_returns_400(self):
        response = self.client.post(
            self.reorder_url(self.rubric.id),
            {
                "order": [
                    str(self.c1.id),
                    str(self.c2.id),
                    str(self.c3.id),
                    str(uuid.uuid4()),
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_duplicate_ids_returns_400(self):
        response = self.client.post(
            self.reorder_url(self.rubric.id),
            {"order": [str(self.c1.id), str(self.c1.id), str(self.c3.id)]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reorder_empty_list_returns_400(self):
        response = self.client.post(
            self.reorder_url(self.rubric.id), {"order": []}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LevelCreateTests(RubricTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.criterion = self.create_criterion(self.rubric)

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_criterion = self.create_criterion(self.other_rubric)

        self.rubric2 = self.create_rubric(self.user)
        self.criterion_rubric2 = self.create_criterion(self.rubric2)

    def level_url(
        self, rubric_id: uuid.UUID | str, criterion_id: uuid.UUID | str
    ) -> str:
        return reverse(
            "level_list_create",
            kwargs={"rubric_id": rubric_id, "criterion_id": criterion_id},
        )

    def test_create_requires_auth(self):
        self.client.credentials()
        response = self.client.post(
            self.level_url(self.rubric.id, self.criterion.id),
            {"score": 1, "descriptor": "Weak"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_success(self):
        payload = {"score": 3, "descriptor": "Excellent argumentation"}
        response = self.client.post(
            self.level_url(self.rubric.id, self.criterion.id), payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        level = CriterionLevel.objects.get(id=response.data["id"])
        self.assertEqual(level.criterion, self.criterion)
        self.assertEqual(level.score, 3)

    def test_create_response_keys(self):
        payload = {"score": 1, "descriptor": "Weak"}
        response = self.client.post(
            self.level_url(self.rubric.id, self.criterion.id), payload, format="json"
        )
        for key in ("id", "score", "descriptor"):
            self.assertIn(key, response.data)

    def test_create_missing_score_returns_400(self):
        response = self.client.post(
            self.level_url(self.rubric.id, self.criterion.id),
            {"descriptor": "No score"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_descriptor_returns_400(self):
        response = self.client.post(
            self.level_url(self.rubric.id, self.criterion.id),
            {"score": 1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_other_user_rubric_returns_404(self):
        response = self.client.post(
            self.level_url(self.other_rubric.id, self.other_criterion.id),
            {"score": 1, "descriptor": "Hack"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_nonexistent_rubric_returns_404(self):
        response = self.client.post(
            self.level_url(uuid.uuid4(), self.criterion.id),
            {"score": 1, "descriptor": "Nope"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_nonexistent_criterion_returns_404(self):
        response = self.client.post(
            self.level_url(self.rubric.id, uuid.uuid4()),
            {"score": 1, "descriptor": "Nope"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_criterion_wrong_rubric_returns_404(self):
        response = self.client.post(
            self.level_url(self.rubric.id, self.criterion_rubric2.id),
            {"score": 1, "descriptor": "Mismatch"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LevelUpdateTests(RubricTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.criterion = self.create_criterion(self.rubric)
        self.level = self.create_level(self.criterion, score=1, descriptor="Weak")

        self.criterion2 = self.create_criterion(self.rubric)
        self.level_other_criterion = self.create_level(self.criterion2, score=2)

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_criterion = self.create_criterion(self.other_rubric)
        self.other_level = self.create_level(self.other_criterion)

    def level_url(
        self,
        rubric_id: uuid.UUID | str,
        criterion_id: uuid.UUID | str,
        level_id: uuid.UUID | str,
    ) -> str:
        return reverse(
            "level_detail",
            kwargs={
                "rubric_id": rubric_id,
                "criterion_id": criterion_id,
                "level_id": level_id,
            },
        )

    def test_update_requires_auth(self):
        self.client.credentials()
        response = self.client.patch(
            self.level_url(self.rubric.id, self.criterion.id, self.level.id),
            {"score": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_score_success(self):
        response = self.client.patch(
            self.level_url(self.rubric.id, self.criterion.id, self.level.id),
            {"score": 4},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.level.refresh_from_db()
        self.assertEqual(self.level.score, 4)

    def test_update_descriptor_success(self):
        response = self.client.patch(
            self.level_url(self.rubric.id, self.criterion.id, self.level.id),
            {"descriptor": "Very strong"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.level.refresh_from_db()
        self.assertEqual(self.level.descriptor, "Very strong")

    def test_update_other_user_returns_404(self):
        response = self.client.patch(
            self.level_url(
                self.other_rubric.id, self.other_criterion.id, self.other_level.id
            ),
            {"score": 99},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_nonexistent_level_returns_404(self):
        response = self.client.patch(
            self.level_url(self.rubric.id, self.criterion.id, uuid.uuid4()),
            {"score": 99},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_level_wrong_criterion_returns_404(self):
        response = self.client.patch(
            self.level_url(
                self.rubric.id, self.criterion.id, self.level_other_criterion.id
            ),
            {"score": 99},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LevelDeleteTests(RubricTestMixin, APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.user = self.create_user()
        self.other_user = self.create_user()
        self.auth_user(self.user)

        self.rubric = self.create_rubric(self.user)
        self.criterion = self.create_criterion(self.rubric)
        self.level = self.create_level(self.criterion, score=1)
        self.level2 = self.create_level(self.criterion, score=2)

        self.criterion2 = self.create_criterion(self.rubric)
        self.level_other_criterion = self.create_level(self.criterion2, score=3)

        self.other_rubric = self.create_rubric(self.other_user)
        self.other_criterion = self.create_criterion(self.other_rubric)
        self.other_level = self.create_level(self.other_criterion)

    def level_url(
        self,
        rubric_id: uuid.UUID | str,
        criterion_id: uuid.UUID | str,
        level_id: uuid.UUID | str,
    ) -> str:
        return reverse(
            "level_detail",
            kwargs={
                "rubric_id": rubric_id,
                "criterion_id": criterion_id,
                "level_id": level_id,
            },
        )

    def test_delete_requires_auth(self):
        self.client.credentials()
        response = self.client.delete(
            self.level_url(self.rubric.id, self.criterion.id, self.level.id)
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_success(self):
        response = self.client.delete(
            self.level_url(self.rubric.id, self.criterion.id, self.level.id)
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CriterionLevel.objects.filter(id=self.level.id).exists())

    def test_delete_other_user_returns_404(self):
        response = self.client.delete(
            self.level_url(
                self.other_rubric.id, self.other_criterion.id, self.other_level.id
            )
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_level_returns_404(self):
        response = self.client.delete(
            self.level_url(self.rubric.id, self.criterion.id, uuid.uuid4())
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_level_wrong_criterion_returns_404(self):
        response = self.client.delete(
            self.level_url(
                self.rubric.id, self.criterion.id, self.level_other_criterion.id
            )
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
