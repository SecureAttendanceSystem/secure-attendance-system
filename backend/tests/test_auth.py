from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db_session
from app.models.user import User, UserRole


class FakeSession:
    """Stands in for a SQLAlchemy Session so routes can be tested without a database."""

    def __init__(self, user=None):
        self.user = user
        self.added = []
        self.deleted = []
        self.commit_error = None
        self.rolled_back = False

    def get(self, _model, _pk):
        return self.user

    def add(self, obj):
        self.added.append(obj)
        # Mimic the default SQLAlchemy would normally assign on flush.
        if obj.is_active is None:
            obj.is_active = True
        self.user = obj

    def commit(self):
        if self.commit_error is not None:
            raise self.commit_error
        return None

    def rollback(self):
        self.rolled_back = True

    def refresh(self, _obj):
        return None


def make_user(**overrides):
    defaults = dict(
        id=uuid4(),
        email="student@unb.ca",
        full_name="Pat Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    defaults.update(overrides)
    return User(**defaults)


class FakeSigningKey:
    def __init__(self, key):
        self.key = key


class FakeJWKClient:
    def __init__(self, key):
        self._key = key

    def get_signing_key_from_jwt(self, _token):
        return FakeSigningKey(self._key)


@pytest.fixture
def signing_key():
    return ec.generate_private_key(ec.SECP256R1())


def auth_header(monkeypatch, signing_key, user):
    monkeypatch.setattr(
        "app.security.supabase_auth._jwks_client",
        lambda _url: FakeJWKClient(signing_key),
    )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user.id),
            "aud": "authenticated",
            "role": "authenticated",
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        signing_key,
        algorithm="ES256",
    )
    return {"Authorization": f"Bearer {token}"}


def override_session(app, session):
    app.dependency_overrides[get_db_session] = lambda: session


# -- /auth/me -------------------------------------------------------------


def test_me_requires_a_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_rejects_a_garbage_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_returns_the_authenticated_user(app, client, signing_key, monkeypatch):
    user = make_user()
    override_session(app, FakeSession(user))

    response = client.get("/auth/me", headers=auth_header(monkeypatch, signing_key, user))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["email"] == user.email
    assert "password_hash" not in body


def test_me_rejects_a_token_for_a_deactivated_user(app, client, signing_key, monkeypatch):
    user = make_user()
    header = auth_header(monkeypatch, signing_key, user)
    user.is_active = False
    override_session(app, FakeSession(user))

    response = client.get("/auth/me", headers=header)

    assert response.status_code == 401


# -- /auth/signup -----------------------------------------------------------


def test_signup_requires_authentication(client):
    response = client.post(
        "/auth/signup",
        json={"email": "new@unb.ca", "full_name": "New Person", "password": "password123"},
    )
    assert response.status_code == 401


def test_signup_rejects_a_non_admin_caller(app, client, signing_key, monkeypatch):
    student = make_user(role=UserRole.STUDENT)
    override_session(app, FakeSession(student))

    response = client.post(
        "/auth/signup",
        json={"email": "new@unb.ca", "full_name": "New Person", "password": "password123"},
        headers=auth_header(monkeypatch, signing_key, student),
    )

    assert response.status_code == 403


def test_signup_creates_a_user_when_called_by_an_admin(app, client, settings, signing_key, monkeypatch):
    admin = make_user(email="admin@unb.ca", role=UserRole.ADMIN)
    session = FakeSession(admin)
    override_session(app, session)

    new_id = str(uuid4())

    def fake_post(url, **_kwargs):
        assert url == f"{settings.supabase_url}/auth/v1/admin/users"
        return httpx.Response(200, json={"id": new_id})

    monkeypatch.setattr(httpx, "post", fake_post)

    response = client.post(
        "/auth/signup",
        json={
            "email": "New.Student@UNB.ca",
            "full_name": "New Student",
            "password": "password123",
            "role": "professor",
        },
        headers=auth_header(monkeypatch, signing_key, admin),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == new_id
    assert body["email"] == "new.student@unb.ca"
    assert body["role"] == "professor"

    created = session.added[0]
    assert str(created.id) == new_id


def test_signup_rejects_a_duplicate_email_from_supabase(app, client, settings, signing_key, monkeypatch):
    admin = make_user(email="admin@unb.ca", role=UserRole.ADMIN)
    override_session(app, FakeSession(admin))

    def fake_post(_url, **_kwargs):
        return httpx.Response(422, json={"error_code": "email_exists", "msg": "already registered"})

    monkeypatch.setattr(httpx, "post", fake_post)

    response = client.post(
        "/auth/signup",
        json={"email": "dup@unb.ca", "full_name": "Dup", "password": "password123"},
        headers=auth_header(monkeypatch, signing_key, admin),
    )

    assert response.status_code == 409


def test_signup_rolls_back_the_supabase_account_on_a_local_conflict(
    app, client, settings, signing_key, monkeypatch
):
    admin = make_user(email="admin@unb.ca", role=UserRole.ADMIN)
    session = FakeSession(admin)
    session.commit_error = IntegrityError("INSERT", {}, Exception("duplicate key"))
    override_session(app, session)

    new_id = str(uuid4())
    deleted = []

    def fake_post(_url, **_kwargs):
        return httpx.Response(200, json={"id": new_id})

    def fake_delete(url, **_kwargs):
        deleted.append(url)
        return httpx.Response(200, json={})

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "delete", fake_delete)

    response = client.post(
        "/auth/signup",
        json={"email": "dup@unb.ca", "full_name": "Dup", "password": "password123"},
        headers=auth_header(monkeypatch, signing_key, admin),
    )

    assert response.status_code == 409
    assert session.rolled_back is True
    assert deleted == [f"{settings.supabase_url}/auth/v1/admin/users/{new_id}"]
