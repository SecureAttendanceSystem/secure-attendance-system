from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.security.supabase_auth import _jwks_client, decode_supabase_token


@pytest.fixture
def signing_key():
    return ec.generate_private_key(ec.SECP256R1())


class FakeSigningKey:
    def __init__(self, key):
        self.key = key


class FakeJWKClient:
    def __init__(self, key):
        self._key = key

    def get_signing_key_from_jwt(self, _token):
        return FakeSigningKey(self._key)


@pytest.fixture(autouse=True)
def clear_jwks_cache():
    _jwks_client.cache_clear()
    yield
    _jwks_client.cache_clear()


def make_token(signing_key, **claim_overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "e2338ef7-4cc5-4766-8df7-2ffc460c86bd",
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    claims.update(claim_overrides)
    return jwt.encode(claims, signing_key, algorithm="ES256")


def test_decode_supabase_token_accepts_a_validly_signed_token(monkeypatch, settings, signing_key):
    token = make_token(signing_key)
    monkeypatch.setattr(
        "app.security.supabase_auth._jwks_client",
        lambda _url: FakeJWKClient(signing_key),
    )

    payload = decode_supabase_token(token, settings)

    assert payload["sub"] == "e2338ef7-4cc5-4766-8df7-2ffc460c86bd"


def test_decode_supabase_token_rejects_a_token_signed_by_a_different_key(monkeypatch, settings, signing_key):
    other_key = ec.generate_private_key(ec.SECP256R1())
    token = make_token(other_key)
    monkeypatch.setattr(
        "app.security.supabase_auth._jwks_client",
        lambda _url: FakeJWKClient(signing_key),
    )

    with pytest.raises(jwt.InvalidSignatureError):
        decode_supabase_token(token, settings)


def test_decode_supabase_token_rejects_an_expired_token(monkeypatch, settings, signing_key):
    now = datetime.now(timezone.utc)
    token = make_token(signing_key, iat=now - timedelta(hours=2), exp=now - timedelta(hours=1))
    monkeypatch.setattr(
        "app.security.supabase_auth._jwks_client",
        lambda _url: FakeJWKClient(signing_key),
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_supabase_token(token, settings)


def test_decode_supabase_token_rejects_the_wrong_audience(monkeypatch, settings, signing_key):
    token = make_token(signing_key, aud="some-other-audience")
    monkeypatch.setattr(
        "app.security.supabase_auth._jwks_client",
        lambda _url: FakeJWKClient(signing_key),
    )

    with pytest.raises(jwt.InvalidAudienceError):
        decode_supabase_token(token, settings)
