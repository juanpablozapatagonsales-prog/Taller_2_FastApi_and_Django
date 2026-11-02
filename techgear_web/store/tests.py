import json
import re
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .api_client import FastAPIUnavailable

User = get_user_model()


def upstream_response(status_code, body):
    response = Mock()
    response.status_code = status_code
    response.is_success = 200 <= status_code < 300
    response.json.return_value = body
    return response


class StorePageTests(TestCase):
    def test_homepage_renders_responsive_store(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La tecnología")
        self.assertContains(response, "store/css/site.css")
        self.assertContains(response, "store/js/site.js")
        self.assertIn("csrftoken", response.cookies)


class UserEndpointTests(TestCase):
    def setUp(self):
        self.valid_user = {
            "username": "camila",
            "email": "camila@example.com",
            "password": "unaclave-larga-y-segura-2026",
        }
        self.mongo_user = {
            "id": "0123456789abcdef01234567",
            "username": "camila",
            "email": "camila@example.com",
        }
        self.auth_response = {
            **self.mongo_user,
            "access_token": "signed-by-fastapi",
            "token_type": "bearer",
        }

    def post_json(self, path, payload):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )

    @patch("techgear_web.store.views.call_fastapi")
    def test_registers_through_fastapi_and_sets_its_jwt_cookie(self, call_fastapi):
        call_fastapi.return_value = upstream_response(201, self.auth_response)

        response = self.post_json("/api/usuarios/", self.valid_user)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"user": self.mongo_user})
        self.assertEqual(
            call_fastapi.call_args.args,
            ("POST", "/usuarios/"),
        )
        self.assertEqual(call_fastapi.call_args.kwargs["payload"], self.valid_user)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(response.cookies["techgear_access"].value, "signed-by-fastapi")
        self.assertTrue(response.cookies["techgear_access"]["httponly"])

    @patch("techgear_web.store.views.call_fastapi")
    def test_duplicate_email_error_comes_from_mongo_api(self, call_fastapi):
        call_fastapi.return_value = upstream_response(
            400,
            {"detail": "El correo ya está registrado"},
        )

        response = self.post_json("/api/usuarios/", self.valid_user)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "El correo ya está registrado")
        self.assertEqual(User.objects.count(), 0)

    @patch("techgear_web.store.views.call_fastapi")
    def test_fastapi_validation_errors_are_returned_to_the_form(self, call_fastapi):
        call_fastapi.return_value = upstream_response(
            422,
            {
                "detail": [
                    {
                        "loc": ["body", "email"],
                        "msg": "value is not a valid email address",
                        "type": "value_error",
                    }
                ]
            },
        )

        response = self.post_json("/api/usuarios/", self.valid_user)

        self.assertEqual(response.status_code, 422)
        self.assertIn("email", response.json()["fields"])

    @patch("techgear_web.store.views.call_fastapi")
    def test_login_uses_fastapi_and_sets_jwt_cookie(self, call_fastapi):
        call_fastapi.return_value = upstream_response(200, self.auth_response)
        payload = {"email": self.valid_user["email"], "password": self.valid_user["password"]}

        response = self.post_json("/api/usuarios/login/", payload)

        self.assertEqual(response.status_code, 200)
        call_fastapi.assert_called_once_with("POST", "/usuarios/login", payload=payload)
        self.assertEqual(response.cookies["techgear_access"].value, "signed-by-fastapi")

    @patch("techgear_web.store.views.call_fastapi")
    def test_current_user_uses_mongo_api_with_cookie_token(self, call_fastapi):
        self.client.cookies["techgear_access"] = "signed-by-fastapi"
        call_fastapi.return_value = upstream_response(200, self.mongo_user)

        response = self.client.get("/api/usuarios/me/")

        self.assertEqual(response.status_code, 200)
        call_fastapi.assert_called_once_with(
            "GET",
            "/usuarios/me",
            access_token="signed-by-fastapi",
        )
        self.assertEqual(response.json(), {"user": self.mongo_user})

    @patch("techgear_web.store.views.call_fastapi")
    def test_current_user_forwards_bearer_token(self, call_fastapi):
        call_fastapi.return_value = upstream_response(200, self.mongo_user)

        response = self.client.get(
            "/api/usuarios/me/",
            HTTP_AUTHORIZATION="Bearer api-token",
        )

        self.assertEqual(response.status_code, 200)
        call_fastapi.assert_called_once_with(
            "GET",
            "/usuarios/me",
            access_token="api-token",
        )

    @patch("techgear_web.store.views.call_fastapi")
    def test_expired_or_invalid_token_clears_cookie(self, call_fastapi):
        self.client.cookies["techgear_access"] = "expired-token"
        call_fastapi.return_value = upstream_response(
            401,
            {"detail": "Token de acceso inválido o expirado"},
        )

        response = self.client.get("/api/usuarios/me/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.cookies["techgear_access"].value, "")

    @patch("techgear_web.store.views.call_fastapi")
    def test_missing_token_returns_empty_success_without_calling_fastapi(self, call_fastapi):
        response = self.client.get("/api/usuarios/me/")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        call_fastapi.assert_not_called()

    def test_logout_clears_jwt_cookie(self):
        self.client.cookies["techgear_access"] = "signed-by-fastapi"

        response = self.post_json("/api/usuarios/logout/", {})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["techgear_access"].value, "")

    def test_malformed_json_is_reported_without_calling_fastapi(self):
        with patch("techgear_web.store.views.call_fastapi") as call_fastapi:
            response = self.client.post(
                "/api/usuarios/",
                data="{",
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("JSON", response.json()["error"])
        call_fastapi.assert_not_called()

    @patch("techgear_web.store.views.call_fastapi", side_effect=FastAPIUnavailable)
    def test_fastapi_unavailable_returns_service_error(self, call_fastapi):
        response = self.post_json("/api/usuarios/", self.valid_user)

        self.assertEqual(response.status_code, 503)
        self.assertIn("FastAPI", response.json()["error"])

    @patch("techgear_web.store.views.call_fastapi")
    def test_browser_registration_passes_django_csrf_validation(self, call_fastapi):
        call_fastapi.return_value = upstream_response(201, self.auth_response)
        client = Client(enforce_csrf_checks=True)
        homepage = client.get("/")
        token = re.search(
            rb'name="csrfmiddlewaretoken" value="([^"]+)"',
            homepage.content,
        ).group(1).decode()

        response = client.post(
            "/api/usuarios/",
            data=json.dumps(self.valid_user),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 201)
