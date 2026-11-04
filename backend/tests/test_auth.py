from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db_session
from app.models.user import User, UserRole
from app.security.passwords import hash_password
from app.security.tokens import create_access_token


class FakeSession:
    """Stands in for a SQLAlchemy Session so routes can be tested without a database."""

    def __init__(self, user=None):
        self.user = user
        self.added = []
        self.rolled_back = False
        self.commit_error = None

    def scalar(self, _statement):
        return self.user

    def get(self, _model, _pk):
        return self.user

    def add(self, obj):
        self.added.append(obj)
        # Mimic the defaults SQLAlchemy would normally assign on flush.
        if obj.id is None:
            obj.id = uuid4()
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
        password_hash=hash_password("Correct-Password1"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    defaults.update(overrides)
    return User(**defaults)


def override_session(app, session):
    app.dependency_overrides[get_db_session] = lambda: session


def auth_header(app, settings, user):
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    return {"Authorization": f"Bearer {token}"}


# -- /auth/login --------------------------------------------------------


def test_login_succeeds_with_correct_credentials(app, client):
    user = make_user()
    override_session(app, FakeSession(user))

    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": "Correct-Password1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == user.email
    assert body["user"]["role"] == "student"
    assert "password" not in response.text


def test_login_rejects_wrong_password(app, client):
    user = make_user()
    override_session(app, FakeSession(user))

    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


@pytest.mark.parametrize("password", ["whatever123", "werkzeug.security"])
def test_login_rejects_unknown_email_with_the_same_message(app, client, password):
    override_session(app, FakeSession(user=None))

    response = client.post(
        "/auth/login",
        json={"email": "nobody@unb.ca", "password": password},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


def test_login_rejects_an_inactive_account(app, client):
    user = make_user(is_active=False)
    override_session(app, FakeSession(user))

    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": "Correct-Password1"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Account is disabled"}


def test_login_rejects_malformed_request_body(client):
    response = client.post("/auth/login", json={"email": "not-an-email", "password": ""})
    assert response.status_code == 422


# -- /auth/me -------------------------------------------------------------


def test_me_requires_a_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_rejects_a_garbage_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_returns_the_authenticated_user(app, client, settings):
    user = make_user()
    override_session(app, FakeSession(user))

    response = client.get("/auth/me", headers=auth_header(app, settings, user))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["email"] == user.email
    assert "password_hash" not in body


def test_me_rejects_a_token_for_a_deactivated_user(app, client, settings):
    user = make_user()
    header = auth_header(app, settings, user)
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


def test_signup_rejects_a_non_admin_caller(app, client, settings):
    student = make_user(role=UserRole.STUDENT)
    override_session(app, FakeSession(student))

    response = client.post(
        "/auth/signup",
        json={"email": "new@unb.ca", "full_name": "New Person", "password": "password123"},
        headers=auth_header(app, settings, student),
    )

    assert response.status_code == 403


def test_signup_creates_a_user_when_called_by_an_admin(app, client, settings):
    admin = make_user(email="admin@unb.ca", role=UserRole.ADMIN)
    session = FakeSession(admin)
    override_session(app, session)

    response = client.post(
        "/auth/signup",
        json={
            "email": "New.Student@UNB.ca",
            "full_name": "New Student",
            "password": "password123",
            "role": "professor",
        },
        headers=auth_header(app, settings, admin),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new.student@unb.ca"
    assert body["role"] == "professor"
    assert "password" not in response.text

    created = session.added[0]
    assert created.password_hash != "password123"


def test_signup_rejects_a_duplicate_email(app, client, settings):
    admin = make_user(email="admin@unb.ca", role=UserRole.ADMIN)
    session = FakeSession(admin)
    session.commit_error = IntegrityError("INSERT", {}, Exception("duplicate key"))
    override_session(app, session)

    response = client.post(
        "/auth/signup",
        json={"email": "dup@unb.ca", "full_name": "Dup", "password": "password123"},
        headers=auth_header(app, settings, admin),
    )

    assert response.status_code == 409
    assert session.rolled_back is True
