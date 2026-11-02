import httpx
from django.conf import settings


class FastAPIUnavailable(Exception):
    pass


def call_fastapi(method, path, *, payload=None, access_token=None):
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        with httpx.Client(timeout=settings.FASTAPI_TIMEOUT) as client:
            return client.request(
                method,
                f"{settings.FASTAPI_BASE_URL}{path}",
                json=payload,
                headers=headers,
            )
    except httpx.RequestError as error:
        raise FastAPIUnavailable from error
