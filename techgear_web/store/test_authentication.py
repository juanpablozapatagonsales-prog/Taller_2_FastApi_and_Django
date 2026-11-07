from unittest.mock import Mock, patch

import httpx
import requests
from django.conf import settings
from django.test import TestCase, override_settings

from .api_client import FastAPIUnavailable, SessionExpired, call_fastapi
from .services import listar_productos


def set_session(client, values):
    session = client.session
    session.update(values)
    session.save()
    client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key


class CustomerAuthenticationTests(TestCase):
    def setUp(self):
        self.usuario = {
            "id": "0123456789abcdef01234567",
            "username": "cliente",
            "correo": "cliente@example.com",
            "rol": "cliente",
            "access_token": "jwt-de-fastapi",
            "token_type": "bearer",
        }

    def signup_data(self, **overrides):
        data = {
            "username": "cliente",
            "correo": "cliente@example.com",
            "password1": "A-long-password-2026!",
            "password2": "A-long-password-2026!",
        }
        data.update(overrides)
        return data

    @patch("techgear_web.store.views.iniciar_sesion")
    @patch("techgear_web.store.views.registrar_usuario")
    def test_registration_calls_fastapi_then_signs_in(self, registrar, iniciar):
        iniciar.return_value = self.usuario

        response = self.client.post("/registro/", self.signup_data())

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        registrar.assert_called_once_with(
            {
                "username": "cliente",
                "correo": "cliente@example.com",
                "password": "A-long-password-2026!",
            }
        )
        iniciar.assert_called_once_with(
            {
                "correo": "cliente@example.com",
                "password": "A-long-password-2026!",
            }
        )
        self.assertEqual(
            dict(response.wsgi_request.session),
            {
                "access_token": "jwt-de-fastapi",
                "id": "0123456789abcdef01234567",
                "username": "cliente",
                "correo": "cliente@example.com",
                "rol": "cliente",
            },
        )
        self.assertNotContains(response, "jwt-de-fastapi", status_code=302)

    @patch("techgear_web.store.views.registrar_usuario")
    def test_registration_requires_matching_passwords(self, registrar):
        response = self.client.post(
            "/registro/",
            self.signup_data(password2="otra-clave-larga"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Las dos contraseñas no coinciden.")
        registrar.assert_not_called()

    @patch("techgear_web.store.views.iniciar_sesion")
    def test_customer_login_uses_email_and_saves_only_session_identity(self, iniciar):
        iniciar.return_value = self.usuario

        response = self.client.post(
            "/ingresar/",
            {"correo": "cliente@example.com", "password": "una-clave"},
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        iniciar.assert_called_once_with(
            {"correo": "cliente@example.com", "password": "una-clave"}
        )
        self.assertEqual(response.wsgi_request.session["access_token"], "jwt-de-fastapi")
        self.assertEqual(response.wsgi_request.session["rol"], "cliente")
        self.assertNotIn("password", response.wsgi_request.session)

    @patch("techgear_web.store.views.iniciar_sesion")
    def test_wrong_password_is_shown_in_spanish(self, iniciar):
        from .services import ErrorAPI

        iniciar.side_effect = ErrorAPI(
            "El correo o la contraseña no son correctos"
        )

        response = self.client.post(
            "/ingresar/",
            {"correo": "cliente@example.com", "password": "incorrecta"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El correo o la contraseña no son correctos")
        self.assertNotIn("access_token", response.wsgi_request.session)

    def test_registration_validates_password_length_and_browser_field_names(self):
        response = self.client.get("/registro/")

        self.assertContains(response, 'name="password1"')
        self.assertContains(response, 'name="password2"')
        self.assertContains(response, 'minlength="8"')
        self.assertContains(response, 'name="correo"')

    def test_logout_is_post_only_and_flushes_the_session(self):
        set_session(
            self.client,
            {
                "access_token": "jwt-de-fastapi",
                "id": self.usuario["id"],
                "username": "cliente",
                "correo": "cliente@example.com",
                "rol": "cliente",
            },
        )

        response = self.client.get("/salir/")
        self.assertEqual(response.status_code, 405)

        response = self.client.post("/salir/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(dict(response.wsgi_request.session), {})


class AdministratorAccessTests(TestCase):
    def setUp(self):
        self.admin = {
            "id": "0123456789abcdef01234568",
            "username": "administrador",
            "correo": "admin@example.com",
            "rol": "admin",
            "access_token": "admin-jwt",
            "token_type": "bearer",
        }

    @patch("techgear_web.store.views.iniciar_sesion")
    def test_admin_login_rejects_customer_role(self, iniciar):
        iniciar.return_value = {**self.admin, "rol": "cliente"}

        response = self.client.post(
            "/admin-ingresar/",
            {"correo": "cliente@example.com", "password": "clave-segura"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "No tienes permiso para entrar como administrador.",
        )
        self.assertNotIn("access_token", response.wsgi_request.session)

    @patch("techgear_web.store.views.iniciar_sesion")
    def test_admin_login_saves_session_and_redirects_to_dashboard(self, iniciar):
        iniciar.return_value = self.admin

        response = self.client.post(
            "/admin-ingresar/",
            {"correo": "admin@example.com", "password": "clave-segura"},
        )

        self.assertRedirects(
            response,
            "/dashboard/",
            fetch_redirect_response=False,
        )
        self.assertEqual(response.wsgi_request.session["rol"], "admin")
        self.assertNotIn("password", response.wsgi_request.session)

    @patch("techgear_web.store.views.listar_productos")
    def test_dashboard_requires_login_and_admin_role(self, listar):
        anonymous = self.client.get("/dashboard/")
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn("/ingresar/", anonymous["Location"])

        set_session(
            self.client,
            {
                "access_token": "cliente-jwt",
                "id": "0123456789abcdef01234567",
                "username": "cliente",
                "correo": "cliente@example.com",
                "rol": "cliente",
            },
        )
        customer = self.client.get("/dashboard/", follow=True)

        self.assertContains(
            customer,
            "No tienes permiso para entrar como administrador.",
        )
        listar.assert_called_once_with()

    @patch("techgear_web.store.views.listar_productos", side_effect=SessionExpired)
    def test_expired_api_token_flushes_session_and_redirects_to_login(self, listar):
        set_session(
            self.client,
            {
                "access_token": "expirado",
                "id": self.admin["id"],
                "username": self.admin["username"],
                "correo": self.admin["correo"],
                "rol": "admin",
            },
        )

        response = self.client.get("/dashboard/", follow=True)

        self.assertRedirects(response, "/ingresar/")
        self.assertContains(
            response,
            "Tu sesión expiró, inicia sesión de nuevo.",
        )
        self.assertEqual(dict(response.wsgi_request.session), {})
        listar.assert_called_once_with(access_token="expirado")

    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_cookie_session_security_settings(self):
        from django.conf import settings

        self.assertEqual(
            settings.SESSION_ENGINE,
            "django.contrib.sessions.backends.signed_cookies",
        )
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertTrue(settings.SESSION_COOKIE_SECURE)


class ApiClientAuthenticationTests(TestCase):
    @patch("techgear_web.store.services.requests.request")
    def test_service_sends_bearer_token_and_keeps_timeout(self, pedir):
        response = Mock()
        response.status_code = 200
        response.ok = True
        response.json.return_value = []
        pedir.return_value = response

        self.assertEqual(listar_productos("jwt-de-prueba"), [])
        self.assertEqual(
            pedir.call_args.kwargs["headers"],
            {"Authorization": "Bearer jwt-de-prueba"},
        )
        self.assertEqual(pedir.call_args.kwargs["timeout"], 5)

    @patch("techgear_web.store.services.requests.request")
    def test_service_treats_api_401_as_expired_session(self, pedir):
        response = Mock(status_code=401)
        pedir.return_value = response

        with self.assertRaises(SessionExpired):
            listar_productos("jwt-expirado")

    @patch("techgear_web.store.api_client.httpx.Client")
    def test_api_client_also_sends_bearer_token(self, client_type):
        response = Mock(status_code=200)
        client_type.return_value.__enter__.return_value.request.return_value = response

        result = call_fastapi("GET", "/usuarios/me", access_token="jwt-de-prueba")

        self.assertIs(result, response)
        self.assertEqual(
            client_type.return_value.__enter__.return_value.request.call_args.kwargs[
                "headers"
            ],
            {"Authorization": "Bearer jwt-de-prueba"},
        )

    @patch("techgear_web.store.api_client.httpx.Client")
    def test_api_client_treats_401_as_expired_session(self, client_type):
        response = Mock(status_code=401)
        client_type.return_value.__enter__.return_value.request.return_value = response

        with self.assertRaises(SessionExpired):
            call_fastapi("GET", "/usuarios/me", access_token="jwt-expirado")

    @patch("techgear_web.store.services.requests.request")
    def test_service_keeps_connection_error_message(self, pedir):
        pedir.side_effect = requests.ConnectionError

        from .services import ErrorAPI

        with self.assertRaisesMessage(ErrorAPI, "No se pudo conectar con FastAPI."):
            listar_productos()

    @patch("techgear_web.store.api_client.httpx.Client")
    def test_api_client_keeps_connection_error(self, client_type):
        client_type.return_value.__enter__.return_value.request.side_effect = (
            httpx.ConnectError("unavailable")
        )

        with self.assertRaises(FastAPIUnavailable):
            call_fastapi("GET", "/productos/")
