from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from pydantic import SecretStr

from app.models.user import UserRole
from app.security.passwords import hash_password, verify_password
from app.security.tokens import create_access_token, decode_access_token


def test_hashed_password_is_not_the_plaintext():
    hashed = hash_password("correct-password")
    assert hashed != "correct-password"


def test_verify_password_accepts_the_matching_password():
    hashed = hash_password("correct-password")
    assert verify_password("correct-password", hashed) is True


def test_verify_password_rejects_a_wrong_password():
    hashed = hash_password("correct-password")
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_rejects_when_no_hash_exists():
    # Used for a login attempt against an email that has no user row.
    assert verify_password("anything", None) is False


def test_verify_password_rejects_a_hash_in_an_unrecognized_scheme():
    # e.g. a bcrypt hash ("$2a$06$...") seeded by something other than
    # generate_password_hash; check_password_hash can't parse it and raises
    # ValueError, which must not become an unhandled 500 during login.
    bcrypt_like_hash = "$2a$06$" + "a" * 53
    assert verify_password("whatever", bcrypt_like_hash) is False


def test_access_token_round_trips_user_id_and_role(settings):
    user_id = uuid4()
    token = create_access_token(user_id=user_id, role=UserRole.PROFESSOR, settings=settings)
    payload = decode_access_token(token, settings)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "professor"


def test_expired_token_is_rejected(settings):
    payload = {
        "sub": str(uuid4()),
        "role": "student",
        "iat": datetime.now(timezone.utc) - timedelta(minutes=10),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token, settings)


def test_token_signed_with_a_different_secret_is_rejected(settings):
    user_id = uuid4()
    token = create_access_token(user_id=user_id, role=UserRole.STUDENT, settings=settings)
    other_settings = settings.model_copy(
        update={"jwt_secret_key": SecretStr("a-completely-different-secret-value")}
    )
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token, other_settings)
