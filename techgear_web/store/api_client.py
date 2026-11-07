import httpx
from django.conf import settings


class FastAPIUnavailable(Exception):
    pass


class SessionExpired(Exception):
    pass


def call_fastapi(method, path, *, payload=None, access_token=None, params=None):
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        with httpx.Client(timeout=settings.FASTAPI_TIMEOUT) as client:
            response = client.request(
                method,
                f"{settings.API_URL.rstrip('/')}/{path.lstrip('/')}",
                json=payload,
                headers=headers,
                params=params,
            )
            if response.status_code == 401 and access_token:
                raise SessionExpired
            return response
    except SessionExpired:
        raise
    except httpx.RequestError as error:
        raise FastAPIUnavailable from error
