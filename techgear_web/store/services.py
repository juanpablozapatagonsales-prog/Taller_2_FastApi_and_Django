import requests
from django.conf import settings

from .api_client import SessionExpired


class ErrorAPI(Exception):
    """Error corto y entendible al comunicarse con FastAPI."""


def _pedir_api(metodo, ruta, datos=None, access_token=None):
    url = f"{settings.API_URL.rstrip('/')}/{ruta.lstrip('/')}"
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    try:
        respuesta = requests.request(
            metodo,
            url,
            json=datos,
            headers=headers,
            timeout=settings.API_TIMEOUT,
        )
    except requests.Timeout as error:
        raise ErrorAPI("FastAPI tardó demasiado en responder.") from error
    except requests.ConnectionError as error:
        raise ErrorAPI("No se pudo conectar con FastAPI.") from error
    except requests.RequestException as error:
        raise ErrorAPI("Ocurrió un error al consultar FastAPI.") from error

    if respuesta.status_code == 401 and access_token:
        raise SessionExpired

    try:
        contenido = respuesta.json()
    except ValueError as error:
        raise ErrorAPI("FastAPI devolvió una respuesta que no es JSON.") from error

    if not respuesta.ok:
        if isinstance(contenido, dict):
            detalle = contenido.get("detail", contenido.get("mensaje"))
            if isinstance(detalle, str) and detalle:
                raise ErrorAPI(detalle)
        if respuesta.status_code == 404:
            raise ErrorAPI("El producto no existe.")
        if respuesta.status_code == 422:
            raise ErrorAPI("Revisa los datos del producto.")
        raise ErrorAPI("FastAPI no pudo completar la solicitud.")

    return contenido


def registrar_usuario(datos):
    usuario = _pedir_api("POST", "/usuarios/registro", datos)
    if not isinstance(usuario, dict):
        raise ErrorAPI("FastAPI devolvió una respuesta de registro inválida.")
    return usuario


def iniciar_sesion(datos):
    usuario = _pedir_api("POST", "/usuarios/login", datos)
    if not isinstance(usuario, dict):
        raise ErrorAPI("FastAPI devolvió una respuesta de inicio de sesión inválida.")
    return usuario


def listar_productos(access_token=None):
    productos = _pedir_api("GET", "/productos/", access_token=access_token)
    if not isinstance(productos, list):
        raise ErrorAPI("FastAPI devolvió una lista de productos inválida.")
    return productos


def obtener_producto(producto_id, access_token=None):
    producto = _pedir_api(
        "GET",
        f"/productos/{producto_id}",
        access_token=access_token,
    )
    if not isinstance(producto, dict):
        raise ErrorAPI("FastAPI devolvió un producto inválido.")
    return producto


def crear_producto(datos, access_token=None):
    producto = _pedir_api(
        "POST",
        "/productos/",
        datos,
        access_token=access_token,
    )
    if not isinstance(producto, dict):
        raise ErrorAPI("FastAPI devolvió un producto inválido.")
    return producto


def editar_producto(producto_id, datos, access_token=None):
    producto = _pedir_api(
        "PUT",
        f"/productos/{producto_id}",
        datos,
        access_token=access_token,
    )
    if not isinstance(producto, dict):
        raise ErrorAPI("FastAPI devolvió un producto inválido.")
    return producto


def eliminar_producto(producto_id, access_token=None):
    resultado = _pedir_api(
        "DELETE",
        f"/productos/{producto_id}",
        access_token=access_token,
    )
    if not isinstance(resultado, dict):
        raise ErrorAPI("FastAPI devolvió una respuesta inválida al eliminar.")
    return resultado


def crear_pedido(producto_id, cantidad, access_token=None):
    pedido = _pedir_api(
        "POST",
        "/pedidos/",
        {
            "productos": [{"producto_id": producto_id, "cantidad": cantidad}],
        },
        access_token=access_token,
    )
    if not isinstance(pedido, dict):
        raise ErrorAPI("FastAPI devolvió un pedido inválido.")
    return pedido
