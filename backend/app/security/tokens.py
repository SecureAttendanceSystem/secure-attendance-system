from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.core.config import Settings
from app.models.user import UserRole


def create_access_token(*, user_id: UUID, role: UserRole, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str, settings: Settings) -> dict:
    # Raises jwt.PyJWTError (expired, malformed, or wrong signature); callers
    # turn that into a 401 without distinguishing the reason to the client.
    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )
