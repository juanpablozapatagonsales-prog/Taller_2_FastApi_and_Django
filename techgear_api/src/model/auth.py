import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt

JWT_ISSUER = "techgear-api"
JWT_LIFETIME = timedelta(hours=8)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32)


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "iat": now,
            "exp": now + JWT_LIFETIME,
            "iss": JWT_ISSUER,
        },
        JWT_SECRET_KEY,
        algorithm="HS256",
    )


def get_token_user_id(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=["HS256"],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except jwt.InvalidTokenError:
        return None

    user_id = payload["sub"]
    return user_id if isinstance(user_id, str) else None
