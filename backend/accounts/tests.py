from django.urls import reverse
from faker import Faker
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User

faker = Faker()
Faker.seed(0)


class AuthEndpointsTests(APITestCase):
    def setUp(self) -> None:
        self.password = "TestPassword123!"
        self.new_password = "NewPassword123!"

    def build_register_payload(self) -> dict[str, str]:
        return {
            "email": faker.unique.email(),
            "full_name": faker.name(),
            "password": self.password,
            "password_confirm": self.password,
        }

    def create_user(
        self,
        email: str | None = None,
        full_name: str | None = None,
        password: str | None = None,
    ) -> User:
        resolved_email = email or faker.unique.email()
        return User.objects.create_user(
            email=resolved_email,
            username=resolved_email,
            full_name=full_name or faker.name(),
            password=password or self.password,
        )

    def login(self, email: str, password: str):
        response = self.client.post(
            reverse("login"),
            {"email": email, "password": password},
            format="json",
        )
        return response

    def authenticate(self, access_token: str) -> None:
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    def authenticate_with_cookie(self, login_response):
        """Set authentication cookies from login response"""
        access_cookie = login_response.cookies.get("access_token")
        if access_cookie:
            self.client.cookies["access_token"] = access_cookie

    def test_register_success(self):
        payload = self.build_register_payload()
        response = self.client.post(reverse("register"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("email", response.data)
        self.assertIn("full_name", response.data)
        self.assertNotIn("password", response.data)
        self.assertNotIn("password_confirm", response.data)

        user = User.objects.get(email=payload["email"])
        self.assertEqual(user.username, payload["email"])  # type: ignore[reportUnknownMemberType]

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
        self.create_user(email="Teacher@Example.com")
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
        # Tokens should be in cookies, not response body
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)

    def test_login_failure(self):
        user = self.create_user()

        response = self.login(user.email, "WrongPassword123!")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue("detail" in response.data or "code" in response.data)

    def test_refresh_success(self):
        user = self.create_user()
        login_response = self.login(user.email, self.password)
        # Refresh token is now in cookie
        refresh_cookie = login_response.cookies.get("refresh_token")

        # Set the cookie for the refresh request
        self.client.cookies["refresh_token"] = refresh_cookie

        response = self.client.post(reverse("token_refresh"), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Token should be in cookie, not response body
        self.assertNotIn("access", response.data)
        self.assertIn("access_token", response.cookies)

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
        self.authenticate_with_cookie(login_response)

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
        self.authenticate_with_cookie(login_response)

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
        self.authenticate_with_cookie(login_response)

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
        # Use cookie authentication instead of extracting from response body
        self.authenticate_with_cookie(login_response)

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


class CookieAuthTests(APITestCase):
    """Tests for cookie-based authentication"""

    def setUp(self) -> None:
        self.password = "TestPassword123!"

    def create_user(
        self,
        email: str | None = None,
        full_name: str | None = None,
        password: str | None = None,
    ) -> User:
        resolved_email = email or faker.unique.email()
        return User.objects.create_user(
            email=resolved_email,
            username=resolved_email,
            full_name=full_name or faker.name(),
            password=password or self.password,
        )

    def login(self, email: str, password: str):
        response = self.client.post(
            reverse("login"),
            {"email": email, "password": password},
            format="json",
        )
        return response

    def test_login_sets_cookies(self):
        """Test that login sets HTTP-only cookies with correct attributes"""
        user = self.create_user()
        response = self.login(user.email, self.password)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that cookies are set
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)

        # Check that tokens are NOT in response body (security)
        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)

    def test_cookie_authentication_works(self):
        """Test that authentication works with cookies (no Bearer token)"""
        user = self.create_user()
        login_response = self.login(user.email, self.password)

        # Set cookies from login response
        self.client.cookies["access_token"] = login_response.cookies["access_token"]

        # Make authenticated request (no Authorization header)
        response = self.client.get(reverse("user_profile"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("email", response.data)
        self.assertEqual(response.data["email"], user.email)

    def test_bearer_token_still_works(self):
        """Test backward compatibility with Bearer token authentication"""
        user = self.create_user()
        login_response = self.login(user.email, self.password)

        # Extract token from cookie and use as Bearer token
        access_token = login_response.cookies["access_token"].value
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # Make authenticated request
        response = self.client.get(reverse("user_profile"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], user.email)

    def test_refresh_with_cookie(self):
        """Test that token refresh works with refresh cookie"""
        user = self.create_user()
        login_response = self.login(user.email, self.password)

        # Set refresh cookie
        self.client.cookies["refresh_token"] = login_response.cookies["refresh_token"]

        # Call refresh without request body (reads from cookie)
        response = self.client.post(reverse("token_refresh"), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that new access token is in cookie
        self.assertIn("access_token", response.cookies)

        # Check that token is NOT in response body
        self.assertNotIn("access", response.data)

    def test_refresh_without_cookie_fails(self):
        """Test that refresh fails without cookie or request body"""
        response = self.client.post(reverse("token_refresh"), format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_clears_cookies(self):
        """Test that logout clears authentication cookies"""
        user = self.create_user()
        login_response = self.login(user.email, self.password)

        # Set cookies
        self.client.cookies["access_token"] = login_response.cookies["access_token"]
        self.client.cookies["refresh_token"] = login_response.cookies["refresh_token"]

        # Call logout
        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)

        # Check that cookies are deleted
        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)
        # Deleted cookies have empty value or max-age of 0
        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")

    def test_logout_without_auth_succeeds(self):
        """Test that logout works even without authentication (idempotent)"""
        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)

    def test_invalid_cookie_rejected(self):
        """Test that invalid cookie is rejected"""
        # Set invalid cookie
        self.client.cookies["access_token"] = "invalid-token-value"

        # Try to make authenticated request
        response = self.client.get(reverse("user_profile"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_cookie_rejected(self):
        """Test that expired token cookie is rejected"""
        from datetime import timedelta

        from rest_framework_simplejwt.tokens import RefreshToken

        user = self.create_user()

        # Create an expired token
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        # Set expiration to the past
        access.set_exp(lifetime=timedelta(seconds=-3600))
        expired_token = str(access)

        # Set expired token as cookie
        self.client.cookies["access_token"] = expired_token

        # Try to make authenticated request
        response = self.client.get(reverse("user_profile"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cookie_security_attributes(self):
        """Test that cookies have correct security attributes"""
        user = self.create_user()
        response = self.login(user.email, self.password)

        access_cookie = response.cookies["access_token"]
        refresh_cookie = response.cookies["refresh_token"]

        # Check HTTP-only flag
        self.assertTrue(access_cookie["httponly"])
        self.assertTrue(refresh_cookie["httponly"])

        # Check SameSite attribute
        self.assertEqual(access_cookie["samesite"], "Lax")
        self.assertEqual(refresh_cookie["samesite"], "Lax")

        # Check secure flag (should be False in development)
        self.assertFalse(access_cookie["secure"])
        self.assertFalse(refresh_cookie["secure"])

        # Check max_age values (60 minutes = 3600 seconds, 7 days = 604800 seconds)
        self.assertEqual(access_cookie["max-age"], 3600)
        self.assertEqual(refresh_cookie["max-age"], 604800)
