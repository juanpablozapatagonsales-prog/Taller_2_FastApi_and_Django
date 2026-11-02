import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .api_client import FastAPIUnavailable, call_fastapi

ACCESS_TOKEN_COOKIE = "techgear_access"
ACCESS_TOKEN_MAX_AGE = 60 * 60 * 8


@ensure_csrf_cookie
def home_view(request):
    return render(request, "store/index.html")


def _json_body(request):
    if request.content_type != "application/json":
        return None, JsonResponse(
            {"error": "El contenido debe enviarse como application/json."},
            status=415,
        )
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"error": "El JSON enviado no es válido."}, status=400)
    if not isinstance(payload, dict):
        return None, JsonResponse({"error": "El cuerpo debe ser un objeto JSON."}, status=400)
    return payload, None


def _api_error(response):
    if response.status_code >= 500:
        return JsonResponse(
            {"error": "El servicio de usuarios no está disponible. Inténtalo más tarde."},
            status=502,
        )

    try:
        body = response.json()
    except ValueError:
        return JsonResponse(
            {"error": "El servicio de usuarios devolvió una respuesta inválida."},
            status=502,
        )

    detail = body.get("detail", body.get("error", "No se pudo completar la solicitud."))
    if isinstance(detail, list):
        fields = {}
        for item in detail:
            if not isinstance(item, dict):
                continue
            location = item.get("loc", [])
            field = location[-1] if location else "non_field_errors"
            fields.setdefault(str(field), []).append(item.get("msg", "Valor no válido."))
        message = "Revisa los datos ingresados."
        return JsonResponse(
            {"error": message, "fields": fields},
            status=response.status_code,
        )

    return JsonResponse({"error": str(detail)}, status=response.status_code)


def _api_json(response):
    try:
        body = response.json()
    except ValueError:
        return None, JsonResponse(
            {"error": "El servicio de usuarios devolvió una respuesta inválida."},
            status=502,
        )
    if not isinstance(body, dict):
        return None, JsonResponse(
            {"error": "El servicio de usuarios devolvió una respuesta inválida."},
            status=502,
        )
    return body, None


def _set_access_cookie(response, access_token):
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        access_token,
        max_age=ACCESS_TOKEN_MAX_AGE,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/",
    )


def _user_payload(body):
    return {
        "id": body["id"],
        "username": body["username"],
        "email": body["email"],
    }


@require_POST
def register_user(request):
    payload, error = _json_body(request)
    if error:
        return error

    try:
        upstream = call_fastapi("POST", "/usuarios/", payload=payload)
    except FastAPIUnavailable:
        return JsonResponse(
            {"error": "No se pudo conectar con FastAPI. Verifica que esté ejecutándose."},
            status=503,
        )
    if not upstream.is_success:
        return _api_error(upstream)

    body, error = _api_json(upstream)
    if error:
        return error
    access_token = body.get("access_token")
    if not access_token or not all(key in body for key in ("id", "username", "email")):
        return JsonResponse(
            {"error": "FastAPI no devolvió los datos de autenticación esperados."},
            status=502,
        )

    response = JsonResponse({"user": _user_payload(body)}, status=upstream.status_code)
    _set_access_cookie(response, access_token)
    return response


@require_POST
def login_user(request):
    payload, error = _json_body(request)
    if error:
        return error

    try:
        upstream = call_fastapi("POST", "/usuarios/login", payload=payload)
    except FastAPIUnavailable:
        return JsonResponse(
            {"error": "No se pudo conectar con FastAPI. Verifica que esté ejecutándose."},
            status=503,
        )
    if not upstream.is_success:
        return _api_error(upstream)

    body, error = _api_json(upstream)
    if error:
        return error
    access_token = body.get("access_token")
    if not access_token or not all(key in body for key in ("id", "username", "email")):
        return JsonResponse(
            {"error": "FastAPI no devolvió los datos de autenticación esperados."},
            status=502,
        )

    response = JsonResponse({"user": _user_payload(body)})
    _set_access_cookie(response, access_token)
    return response


@require_GET
def current_user(request):
    access_token = request.headers.get("Authorization", "")
    if access_token.startswith("Bearer "):
        access_token = access_token[7:].strip()
    else:
        access_token = request.COOKIES.get(ACCESS_TOKEN_COOKIE, "")

    if not access_token:
        return JsonResponse({}, status=204)

    try:
        upstream = call_fastapi(
            "GET",
            "/usuarios/me",
            access_token=access_token,
        )
    except FastAPIUnavailable:
        return JsonResponse(
            {"error": "No se pudo conectar con FastAPI. Verifica que esté ejecutándose."},
            status=503,
        )
    if not upstream.is_success:
        response = _api_error(upstream)
        if upstream.status_code == 401:
            response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/", samesite="Lax")
        return response

    body, error = _api_json(upstream)
    if error:
        return error
    if not all(key in body for key in ("id", "username", "email")):
        return JsonResponse(
            {"error": "FastAPI devolvió datos de usuario incompletos."},
            status=502,
        )
    return JsonResponse({"user": _user_payload(body)})


@require_POST
def logout_user(request):
    response = JsonResponse({"message": "Sesión cerrada."})
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/", samesite="Lax")
    return response
