from unittest.mock import Mock, patch

import requests
from django.conf import settings
from django.test import Client, TestCase

from .services import (
    ErrorAPI,
    crear_producto,
    editar_producto,
    eliminar_producto,
    listar_productos,
    obtener_producto,
)


def set_session(client, values):
    session = client.session
    session.update(values)
    session.save()
    client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key


def upstream_response(status_code, body):
    response = Mock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.json.return_value = body
    return response


class ProductServiceTests(TestCase):
    product = {
        "id": "0123456789abcdef01234567",
        "nombre": "Teclado",
        "descripcion": "Teclado mecánico",
        "precio": 0,
        "unidades": 5,
        "activo": True,
    }

    @patch("techgear_web.store.services.requests.request")
    def test_public_product_list_uses_api_url_and_timeout(self, pedir):
        pedir.return_value = upstream_response(200, [self.product])

        self.assertEqual(listar_productos(), [self.product])
        self.assertEqual(
            pedir.call_args.args,
            ("GET", "http://127.0.0.1:8001/productos/"),
        )
        self.assertEqual(pedir.call_args.kwargs["timeout"], 5)
        self.assertEqual(pedir.call_args.kwargs["headers"], {})

    @patch("techgear_web.store.services.requests.request")
    def test_write_and_detail_services_send_bearer_token(self, pedir):
        pedir.return_value = upstream_response(200, self.product)
        datos = {key: value for key, value in self.product.items() if key != "id"}
        token = "admin-jwt"

        obtener_producto(self.product["id"], access_token=token)
        crear_producto(datos, access_token=token)
        editar_producto(self.product["id"], datos, access_token=token)
        pedir.return_value = upstream_response(200, {"mensaje": "eliminado"})
        eliminar_producto(self.product["id"], access_token=token)

        self.assertEqual(
            [call.kwargs["headers"] for call in pedir.call_args_list],
            [{"Authorization": "Bearer admin-jwt"}] * 4,
        )
        self.assertEqual(
            [call.args[0] for call in pedir.call_args_list],
            ["GET", "POST", "PUT", "DELETE"],
        )

    @patch("techgear_web.store.services.requests.request")
    def test_api_connection_error_is_understandable(self, pedir):
        pedir.side_effect = requests.ConnectionError

        with self.assertRaisesMessage(ErrorAPI, "No se pudo conectar con FastAPI."):
            listar_productos()

    @patch("techgear_web.store.services.requests.request")
    def test_invalid_json_response_is_reported(self, pedir):
        response = Mock()
        response.status_code = 200
        response.json.side_effect = ValueError
        pedir.return_value = response

        with self.assertRaisesMessage(
            ErrorAPI,
            "FastAPI devolvió una respuesta que no es JSON.",
        ):
            listar_productos()


class StorePageTests(TestCase):
    def setUp(self):
        self.product = {
            "id": "0123456789abcdef01234567",
            "nombre": "Teclado",
            "descripcion": "Teclado mecánico",
            "precio": 120000,
            "unidades": 5,
            "activo": True,
        }

    @patch("techgear_web.store.views.listar_productos")
    def test_homepage_renders_products_and_existing_design(self, listar):
        listar.return_value = [self.product, {**self.product, "activo": False}]

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "lang=\"es\"")
        self.assertContains(response, "bootstrap@5.3.8/dist/css/bootstrap.min.css")
        self.assertContains(response, "Ingresar")
        self.assertContains(response, "Crear cuenta")
        self.assertContains(response, "Teclado")
        self.assertContains(response, 'src="/static/store/images/techgear-mark.svg"')
        self.assertNotContains(response, "jwt-de")
        listar.assert_called_once_with()

    @patch("techgear_web.store.views.listar_productos", return_value=[])
    def test_template_user_context_comes_from_the_jwt_session(self, listar):
        set_session(
            self.client,
            {
                "access_token": "private-jwt",
                "id": "0123456789abcdef01234567",
                "username": "estudiante",
                "correo": "estudiante@example.com",
                "rol": "admin",
            },
        )

        response = self.client.get("/")

        self.assertContains(response, "estudiante")
        self.assertContains(response, 'href="/dashboard/"')
        self.assertContains(response, 'action="/salir/" method="post"')
        self.assertNotContains(response, "private-jwt")
        self.assertNotContains(response, "Ingresar")
        listar.assert_called_once_with()

    @patch("techgear_web.store.views.listar_productos")
    def test_public_products_page_shows_only_active_items(self, listar):
        listar.return_value = [self.product, {**self.product, "activo": False}]

        response = self.client.get("/productos/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teclado")
        self.assertNotContains(response, "Producto oculto")
        listar.assert_called_once_with()


class ProductDashboardTests(TestCase):
    product_id = "0123456789abcdef01234567"

    def setUp(self):
        self.product = {
            "id": self.product_id,
            "nombre": "Studio One",
            "descripcion": "Audífonos inalámbricos",
            "precio": 389000,
            "unidades": 4,
            "activo": True,
        }
        set_session(
            self.client,
            {
                "access_token": "admin-jwt",
                "id": "1123456789abcdef01234567",
                "username": "catalog-admin",
                "correo": "admin@example.com",
                "rol": "admin",
            },
        )

    @patch("techgear_web.store.views.listar_productos")
    def test_dashboard_sends_jwt_and_renders_products(self, listar):
        listar.return_value = [self.product]

        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crear producto")
        self.assertContains(response, "Studio One")
        listar.assert_called_once_with(access_token="admin-jwt")

    @patch("techgear_web.store.views.crear_producto")
    def test_product_create_sends_validated_fields_and_jwt(self, crear):
        crear.return_value = self.product

        response = self.client.post(
            "/dashboard/productos/nuevo/",
            {
                "nombre": "Studio One",
                "descripcion": "Audífonos inalámbricos",
                "precio": "389000",
                "unidades": "4",
                "imagen": "https://example.com/studio-one.jpg",
                "activo": "on",
            },
        )

        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)
        crear.assert_called_once_with(
            {
                "nombre": "Studio One",
                "descripcion": "Audífonos inalámbricos",
                "precio": 389000.0,
                "unidades": 4,
                "imagen": "https://example.com/studio-one.jpg",
                "activo": True,
            },
            access_token="admin-jwt",
        )

    @patch("techgear_web.store.views.editar_producto")
    def test_product_edit_sends_jwt_and_validated_fields(self, editar):
        editar.return_value = self.product

        response = self.client.post(
            f"/dashboard/productos/{self.product_id}/editar/",
            {
                "nombre": "Studio One",
                "descripcion": "Audífonos inalámbricos",
                "precio": "399000",
                "unidades": "4",
                "imagen": "https://example.com/studio-one.jpg",
                "activo": "on",
            },
        )

        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)
        editar.assert_called_once_with(
            self.product_id,
            {
                "nombre": "Studio One",
                "descripcion": "Audífonos inalámbricos",
                "precio": 399000.0,
                "unidades": 4,
                "imagen": "https://example.com/studio-one.jpg",
                "activo": True,
            },
            access_token="admin-jwt",
        )

    @patch("techgear_web.store.views.eliminar_producto")
    def test_delete_is_post_only_and_sends_token(self, eliminar):
        response = self.client.post(
            f"/dashboard/productos/{self.product_id}/eliminar/"
        )

        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)
        eliminar.assert_called_once_with(
            self.product_id,
            access_token="admin-jwt",
        )

    @patch("techgear_web.store.views.crear_producto")
    def test_invalid_product_form_does_not_call_fastapi(self, crear):
        response = self.client.post(
            "/dashboard/productos/nuevo/",
            {"nombre": "", "precio": "-1", "unidades": "-2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este campo es obligatorio.")
        crear.assert_not_called()

    @patch("techgear_web.store.views.obtener_producto")
    def test_delete_has_confirmation_page(self, obtener):
        obtener.return_value = self.product

        response = self.client.get(
            f"/dashboard/productos/{self.product_id}/eliminar/confirmar/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "¿Confirmas que quieres eliminar")
        self.assertContains(response, 'method="post"')
        obtener.assert_called_once_with(self.product_id, access_token="admin-jwt")


class ProductPurchaseTests(TestCase):
    product_id = "0123456789abcdef01234567"

    @patch("techgear_web.store.views.crear_pedido")
    def test_logged_in_customer_creates_order_using_jwt(self, crear_pedido):
        set_session(
            self.client,
            {
                "access_token": "customer-jwt",
                "id": "2123456789abcdef01234567",
                "username": "cliente",
                "correo": "cliente@example.com",
                "rol": "cliente",
            },
        )
        crear_pedido.return_value = {"total": 200000}

        response = self.client.post(
            f"/productos/{self.product_id}/comprar/",
            {"cantidad": "2", "usuario_id": "usuario-ajeno"},
        )

        self.assertRedirects(response, "/productos/", fetch_redirect_response=False)
        crear_pedido.assert_called_once_with(
            self.product_id,
            2,
            access_token="customer-jwt",
        )

    @patch("techgear_web.store.views.crear_pedido")
    def test_anonymous_customer_is_redirected_to_login(self, crear_pedido):
        response = self.client.post(
            f"/productos/{self.product_id}/comprar/",
            {"cantidad": "1"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/ingresar/", response["Location"])
        crear_pedido.assert_not_called()

    @patch("techgear_web.store.views.crear_pedido")
    def test_invalid_quantity_does_not_create_order(self, crear_pedido):
        set_session(
            self.client,
            {
                "access_token": "customer-jwt",
                "id": "2123456789abcdef01234567",
                "username": "cliente",
                "correo": "cliente@example.com",
                "rol": "cliente",
            },
        )

        response = self.client.post(
            f"/productos/{self.product_id}/comprar/",
            {"cantidad": "0"},
        )

        self.assertRedirects(response, "/productos/", fetch_redirect_response=False)
        crear_pedido.assert_not_called()

    @patch("techgear_web.store.views.crear_producto")
    def test_admin_product_actions_require_csrf(self, crear):
        client = Client(enforce_csrf_checks=True)
        set_session(
            client,
            {
                "access_token": "admin-jwt",
                "id": "1123456789abcdef01234567",
                "username": "admin",
                "correo": "admin@example.com",
                "rol": "admin",
            },
        )

        response = client.post(
            "/dashboard/productos/nuevo/",
            {
                "nombre": "Studio One",
                "descripcion": "Audífonos",
                "precio": "100",
                "unidades": "2",
            },
        )

        self.assertEqual(response.status_code, 403)
        crear.assert_not_called()
