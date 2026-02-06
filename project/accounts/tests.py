from django.contrib.auth import get_user_model
from django.urls import reverse
from faker import Faker
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()
faker = Faker()
Faker.seed(0)


class AuthEndpointsTests(APITestCase):
    def setUp(self):
        self.password = "TestPassword123!"
        self.new_password = "NewPassword123!"

    def build_register_payload(self):
        return {
            "email": faker.unique.email(),
            "full_name": faker.name(),
            "password": self.password,
            "password_confirm": self.password,
        }

    def create_user(self, email=None, full_name=None, password=None):
        resolved_email = email or faker.unique.email()
        return User.objects.create_user(
            email=resolved_email,
            username=resolved_email,
            full_name=full_name or faker.name(),
            password=password or self.password,
        )

    def login(self, email, password):
        response = self.client.post(
            reverse("login"),
            {"email": email, "password": password},
            format="json",
        )
        return response

    def authenticate(self, access_token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    def test_register_success(self):
        payload = self.build_register_payload()
        response = self.client.post(reverse("register"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("email", response.data)
        self.assertIn("full_name", response.data)
        self.assertNotIn("password", response.data)
        self.assertNotIn("password_confirm", response.data)

        user = User.objects.get(email=payload["email"])
        self.assertEqual(user.username, payload["email"])

    def test_register_password_mismatch(self):
        payload = self.build_register_payload()
        payload["password_confirm"] = "DifferentPassword123!"

        response = self.client.post(reverse("register"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)

    def test_register_duplicate_email(self):
        existing = self.create_user()
        payload = self.build_register_payload()
        payload["email"] = existing.email
        payload["password_confirm"] = payload["password"]

        response = self.client.post(reverse("register"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_duplicate_email_case_insensitive(self):
        existing = self.create_user(email="Teacher@Example.com")
        payload = self.build_register_payload()
        payload["email"] = "TEACHER@EXAMPLE.COM"
        payload["password_confirm"] = payload["password"]

        response = self.client.post(reverse("register"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_login_success(self):
        user = self.create_user()

        response = self.login(user.email, self.password)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_failure(self):
        user = self.create_user()

        response = self.login(user.email, "WrongPassword123!")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue("detail" in response.data or "code" in response.data)

    def test_refresh_success(self):
        user = self.create_user()
        login_response = self.login(user.email, self.password)
        refresh = login_response.data["refresh"]

        response = self.client.post(
            reverse("token_refresh"), {"refresh": refresh}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_refresh_invalid(self):
        response = self.client.post(
            reverse("token_refresh"), {"refresh": "invalid-token"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue("detail" in response.data or "code" in response.data)

    def test_profile_requires_auth(self):
        response = self.client.get(reverse("user_profile"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get_success(self):
        user = self.create_user()
        login_response = self.login(user.email, self.password)
        self.authenticate(login_response.data["access"])

        response = self.client.get(reverse("user_profile"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("id", response.data)
        self.assertIn("email", response.data)
        self.assertIn("full_name", response.data)
        self.assertIn("created_at", response.data)
        self.assertIn("updated_at", response.data)

    def test_profile_patch_updates_full_name_only(self):
        user = self.create_user()
        login_response = self.login(user.email, self.password)
        self.authenticate(login_response.data["access"])

        new_full_name = faker.name()
        original_email = user.email
        response = self.client.patch(
            reverse("user_profile"),
            {"full_name": new_full_name, "email": faker.unique.email()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.full_name, new_full_name)
        self.assertEqual(user.email, original_email)

    def test_change_password_requires_auth(self):
        response = self.client.post(reverse("change_password"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_invalid_old_password(self):
        user = self.create_user()
        login_response = self.login(user.email, self.password)
        self.authenticate(login_response.data["access"])

        response = self.client.post(
            reverse("change_password"),
            {"old_password": "WrongPassword123!", "new_password": self.new_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", response.data)

    def test_change_password_success(self):
        user = self.create_user()
        login_response = self.login(user.email, self.password)
        self.authenticate(login_response.data["access"])

        response = self.client.post(
            reverse("change_password"),
            {"old_password": self.password, "new_password": self.new_password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)

        old_login = self.login(user.email, self.password)
        self.assertEqual(old_login.status_code, status.HTTP_401_UNAUTHORIZED)
        new_login = self.login(user.email, self.new_password)
        self.assertEqual(new_login.status_code, status.HTTP_200_OK)
