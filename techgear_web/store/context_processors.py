from types import SimpleNamespace


def template_user(request):
    rol = request.session.get("rol")
    return {
        "user": SimpleNamespace(
            is_authenticated=bool(request.session.get("access_token")),
            username=request.session.get("username", ""),
            is_staff=rol == "admin",
        )
    }
