import re
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .api_client import SessionExpired
from .forms import (
    AdminLoginForm,
    CustomerLoginForm,
    CustomerSignupForm,
    ProductForm,
    PurchaseForm,
)
from .services import (
    ErrorAPI,
    crear_producto,
    crear_pedido,
    editar_producto,
    eliminar_producto,
    iniciar_sesion,
    listar_productos,
    obtener_producto,
    registrar_usuario,
)


def _token(request):
    return request.session.get("access_token")


def _guardar_sesion(request, usuario):
    request.session.flush()
    request.session.update(
        {
            "access_token": usuario["access_token"],
            "id": usuario["id"],
            "username": usuario["username"],
            "correo": usuario["correo"],
            "rol": usuario["rol"],
        }
    )


def _sesion_expirada(request):
    request.session.flush()
    messages.error(request, "Tu sesión expiró, inicia sesión de nuevo.")
    return redirect("client-login")


def login_requerido(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not _token(request):
            messages.error(request, "Inicia sesión para continuar.")
            return redirect("client-login")
        try:
            return view_func(request, *args, **kwargs)
        except SessionExpired:
            return _sesion_expirada(request)

    return wrapped_view


def admin_requerido(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not _token(request):
            messages.error(request, "Inicia sesión para continuar.")
            return redirect("client-login")
        if request.session.get("rol") != "admin":
            messages.error(
                request,
                "No tienes permiso para entrar como administrador.",
            )
            return redirect("client-login")
        try:
            return view_func(request, *args, **kwargs)
        except SessionExpired:
            return _sesion_expirada(request)

    return wrapped_view


def _mensaje_error_formulario(form, error):
    if "correo" in str(error).lower() and "registr" in str(error).lower():
        form.add_error("correo", str(error))
    else:
        form.add_error(None, str(error))


@ensure_csrf_cookie
def home_view(request):
    try:
        productos = [
            producto
            for producto in listar_productos()
            if producto.get("activo", False)
        ]
    except ErrorAPI as error:
        messages.error(request, str(error))
        productos = []
    return render(request, "store/index.html", {"productos": productos})


@require_GET
def products_view(request):
    try:
        productos = [
            producto
            for producto in listar_productos()
            if producto.get("activo", False)
        ]
    except ErrorAPI as error:
        messages.error(request, str(error))
        productos = []
    return render(request, "store/public_products.html", {"productos": productos})


@require_http_methods(["GET", "POST"])
def client_signup(request):
    if _token(request):
        return redirect("home")

    form = CustomerSignupForm(
        request.POST if request.method == "POST" else None
    )
    if request.method == "POST" and form.is_valid():
        datos = form.cleaned_data
        try:
            registrar_usuario(
                {
                    "username": datos["username"],
                    "correo": datos["correo"],
                    "password": datos["password1"],
                }
            )
            usuario = iniciar_sesion(
                {
                    "correo": datos["correo"],
                    "password": datos["password1"],
                }
            )
        except ErrorAPI as error:
            _mensaje_error_formulario(form, error)
        else:
            _guardar_sesion(request, usuario)
            messages.success(request, "Cuenta creada correctamente.")
            return redirect("home")

    return render(
        request,
        "store/account_form.html",
        {
            "form": form,
            "titulo": "Crear cuenta",
            "descripcion": "Registra una cuenta de cliente.",
            "texto_boton": "Crear cuenta",
            "enlace_url": "client-login",
            "enlace_texto": "Ya tengo cuenta",
        },
    )


@require_http_methods(["GET", "POST"])
def client_login(request):
    if _token(request):
        return redirect("home")

    form = CustomerLoginForm(
        request.POST if request.method == "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        try:
            usuario = iniciar_sesion(form.cleaned_data)
        except ErrorAPI as error:
            form.add_error(None, str(error))
        else:
            if usuario["rol"] != "cliente":
                form.add_error(None, "Esta cuenta es de administrador. Usa su acceso.")
            else:
                _guardar_sesion(request, usuario)
                messages.success(request, "Sesión iniciada.")
                return redirect("home")

    return render(
        request,
        "store/account_form.html",
        {
            "form": form,
            "titulo": "Iniciar sesión",
            "descripcion": "Ingresa con tu cuenta de cliente.",
            "texto_boton": "Iniciar sesión",
            "enlace_url": "client-signup",
            "enlace_texto": "Crear cuenta",
        },
    )


@require_http_methods(["GET", "POST"])
def admin_login(request):
    if _token(request) and request.session.get("rol") == "admin":
        return redirect("admin-dashboard")

    form = AdminLoginForm(
        request.POST if request.method == "POST" else None,
    )
    if request.method == "POST" and form.is_valid():
        try:
            usuario = iniciar_sesion(form.cleaned_data)
        except ErrorAPI as error:
            form.add_error(None, str(error))
        else:
            if usuario["rol"] != "admin":
                form.add_error(
                    None,
                    "No tienes permiso para entrar como administrador.",
                )
            else:
                _guardar_sesion(request, usuario)
                messages.success(request, "Sesión de administrador iniciada.")
                return redirect("admin-dashboard")

    return render(
        request,
        "store/account_form.html",
        {
            "form": form,
            "titulo": "Acceso de administrador",
            "descripcion": "Ingresa con tu cuenta de administrador.",
            "texto_boton": "Iniciar sesión",
            "enlace_url": "client-login",
            "enlace_texto": "Acceso de cliente",
        },
    )


@require_POST
def logout_view(request):
    request.session.flush()
    messages.success(request, "Sesión cerrada.")
    return redirect(settings.LOGOUT_REDIRECT_URL)


@admin_requerido
@require_GET
def admin_dashboard(request):
    try:
        productos = listar_productos(access_token=_token(request))
    except ErrorAPI as error:
        messages.error(request, str(error))
        productos = []
    return render(request, "store/dashboard.html", {"productos": productos})


@admin_requerido
@require_http_methods(["GET", "POST"])
def new_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        return _save_product_form(request, form)
    form = ProductForm()
    return render(request, "store/product_form.html", {"form": form, "editando": False})


@admin_requerido
@require_http_methods(["GET", "POST"])
def edit_product(request, producto_id):
    if not re.fullmatch(r"[0-9a-fA-F]{24}", producto_id):
        messages.error(request, "El identificador del producto no es válido.")
        return redirect("admin-dashboard")

    if request.method == "POST":
        form = ProductForm(request.POST)
        return _save_product_form(request, form, producto_id)

    try:
        producto = obtener_producto(producto_id, access_token=_token(request))
    except ErrorAPI as error:
        messages.error(request, str(error))
        return redirect("admin-dashboard")

    form = ProductForm(initial=producto)
    return render(
        request,
        "store/product_form.html",
        {"form": form, "editando": True, "producto": producto},
    )


def _save_product_form(request, form, producto_id=None):
    if not form.is_valid():
        return render(
            request,
            "store/product_form.html",
            {
                "form": form,
                "editando": producto_id is not None,
                "producto": {"id": producto_id} if producto_id else None,
            },
        )

    payload = form.cleaned_data.copy()
    payload["precio"] = float(payload["precio"])

    try:
        if producto_id:
            editar_producto(
                producto_id,
                payload,
                access_token=_token(request),
            )
        else:
            crear_producto(payload, access_token=_token(request))
    except ErrorAPI as error:
        messages.error(request, str(error))
        return render(
            request,
            "store/product_form.html",
            {
                "form": form,
                "editando": producto_id is not None,
                "producto": {"id": producto_id} if producto_id else None,
            },
        )

    messages.success(
        request,
        "Producto actualizado." if producto_id else "Producto creado.",
    )
    return redirect("admin-dashboard")


@admin_requerido
@require_GET
def confirm_delete_product(request, producto_id):
    if not re.fullmatch(r"[0-9a-fA-F]{24}", producto_id):
        messages.error(request, "El identificador del producto no es válido.")
        return redirect("admin-dashboard")
    try:
        producto = obtener_producto(producto_id, access_token=_token(request))
    except ErrorAPI as error:
        messages.error(request, str(error))
        return redirect("admin-dashboard")
    return render(
        request,
        "store/product_confirm_delete.html",
        {"producto": producto},
    )


@admin_requerido
@require_POST
def delete_product(request, producto_id):
    if not re.fullmatch(r"[0-9a-fA-F]{24}", producto_id):
        messages.error(request, "El identificador del producto no es válido.")
        return redirect("admin-dashboard")

    try:
        eliminar_producto(producto_id, access_token=_token(request))
    except ErrorAPI as error:
        messages.error(request, str(error))
        return redirect("admin-dashboard")
    messages.success(request, "Producto eliminado.")
    return redirect("admin-dashboard")


@login_requerido
@require_POST
def purchase_product(request, producto_id):
    if not re.fullmatch(r"[0-9a-fA-F]{24}", producto_id):
        messages.error(request, "El identificador del producto no es válido.")
        return redirect("catalog-products")

    form = PurchaseForm(request.POST)
    if not form.is_valid():
        messages.error(request, "La cantidad solicitada no es válida.")
        return redirect("catalog-products")

    try:
        pedido = crear_pedido(
            producto_id,
            form.cleaned_data["cantidad"],
            access_token=_token(request),
        )
    except ErrorAPI as error:
        messages.error(request, str(error))
        return redirect("catalog-products")

    messages.success(
        request,
        f"Pedido creado correctamente. Total: ${pedido['total']:.2f}.",
    )
    return redirect("catalog-products")
