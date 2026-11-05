from functools import lru_cache

import jwt
from jwt import PyJWKClient

from app.core.config import Settings


@lru_cache
def _jwks_client(jwks_url: str) -> PyJWKClient:
    # PyJWKClient caches the fetched key set in-process and only re-fetches
    # when it sees an unrecognized `kid`, so one client per URL is reused
    # across requests instead of hitting the JWKS endpoint every time.
    return PyJWKClient(jwks_url)


def decode_supabase_token(token: str, settings: Settings) -> dict:
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256"],
        audience="authenticated",
    )
