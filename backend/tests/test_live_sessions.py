"""Live sessions and passkey check-in.

Auth works as in test_courses.py: tokens are signed with a throwaway ES256
key and the Supabase JWKS lookup is patched to return it. WebAuthn responses
come from SoftAuthenticator, a software passkey that builds real attestation
and assertion payloads, so py_webauthn's verification runs for real.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import cbor2
import jwt
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import operators
from sqlalchemy.sql.dml import Delete
from sqlalchemy.sql.elements import BinaryExpression, BindParameter, BooleanClauseList
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

from app.api.deps import get_db_session
from app.models.attendance import AttendanceRecord
from app.models.class_session import ClassSession
from app.models.course import Course, CourseInstructor, Enrollment
from app.models.enums import AttendanceStatus, ChallengePurpose, SessionStatus
from app.models.passkey import PasskeyCredential, WebAuthnChallenge
from app.models.user import User, UserRole

SIGNING_KEY = ec.generate_private_key(ec.SECP256R1())
ORIGIN = "http://localhost:3000"
RP_ID = "localhost"


class FakeSigningKey:
    def __init__(self, key):
        self.key = key


class FakeJWKClient:
    def get_signing_key_from_jwt(self, _token):
        return FakeSigningKey(SIGNING_KEY.public_key())


@pytest.fixture(autouse=True)
def fake_supabase_jwks(monkeypatch):
    monkeypatch.setattr(
        "app.security.supabase_auth._jwks_client", lambda _url: FakeJWKClient()
    )


def auth_header(user):
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": str(user.id), "aud": "authenticated", "iat": now, "exp": now + timedelta(hours=1)},
        SIGNING_KEY,
        algorithm="ES256",
    )
    return {"Authorization": f"Bearer {token}"}


# -- Fake database ------------------------------------------------------------------


def _matches(obj, clause):
    """Evaluate the simple WHERE clauses the routes use (==, IN, AND) against an object."""
    if clause is None:
        return True
    if isinstance(clause, BooleanClauseList) and clause.operator is operators.and_:
        return all(_matches(obj, part) for part in clause.clauses)
    if isinstance(clause, BinaryExpression) and isinstance(clause.right, BindParameter):
        left = getattr(obj, clause.left.key)
        right = clause.right.value
        if clause.operator is operators.eq:
            return left == right
        if clause.operator is operators.in_op:
            return left in right
    raise NotImplementedError(f"FakeSession can't evaluate {clause!r}")


def _primary_key(obj):
    columns = sa_inspect(type(obj)).primary_key
    values = tuple(getattr(obj, column.key) for column in columns)
    return values[0] if len(values) == 1 else values


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return list(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None


class FakeSession:
    """An in-memory stand-in for a SQLAlchemy Session holding a flat list of rows."""

    def __init__(self, *objects):
        self.objects = list(objects)
        self.added = []
        self.commits = 0
        self.rolled_back = False
        self.commit_error = None

    def of(self, model):
        return [obj for obj in self.objects if isinstance(obj, model)]

    def get(self, model, pk):
        return next((obj for obj in self.of(model) if _primary_key(obj) == pk), None)

    def scalars(self, statement):
        model = statement.column_descriptions[0]["entity"]
        return FakeResult([obj for obj in self.of(model) if _matches(obj, statement.whereclause)])

    def execute(self, statement):
        assert isinstance(statement, Delete)
        self.objects = [
            obj
            for obj in self.objects
            if obj.__table__ is not statement.table or not _matches(obj, statement.whereclause)
        ]

    def add(self, obj):
        # Mimic the primary-key default SQLAlchemy would assign on flush.
        if getattr(obj, "id", "") is None:
            obj.id = uuid4()
        self.added.append(obj)
        self.objects.append(obj)

    def delete(self, obj):
        self.objects.remove(obj)

    def commit(self):
        if self.commit_error is not None:
            raise self.commit_error
        self.commits += 1

    def rollback(self):
        self.rolled_back = True

    def refresh(self, _obj):
        return None


# -- Software passkey ---------------------------------------------------------------

FLAG_UP, FLAG_UV, FLAG_AT = 0x01, 0x04, 0x40


def b64(data: bytes) -> str:
    return bytes_to_base64url(data)


class SoftAuthenticator:
    """A minimal platform authenticator: one P-256 key, "none" attestation."""

    def __init__(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = uuid4().bytes + uuid4().bytes
        self.sign_count = 0

    def _client_data(self, kind, options, origin):
        return json.dumps(
            {"type": kind, "challenge": options["challenge"], "origin": origin, "crossOrigin": False}
        ).encode()

    def _cose_public_key(self):
        numbers = self.key.public_key().public_numbers()
        return cbor2.dumps(
            {1: 2, 3: -7, -1: 1, -2: numbers.x.to_bytes(32, "big"), -3: numbers.y.to_bytes(32, "big")}
        )

    def register(self, options, *, origin=ORIGIN, flags=FLAG_UP | FLAG_UV | FLAG_AT):
        client_data = self._client_data("webauthn.create", options, origin)
        auth_data = (
            hashlib.sha256(options["rp"]["id"].encode()).digest()
            + bytes([flags])
            + self.sign_count.to_bytes(4, "big")
            + bytes(16)  # AAGUID
            + len(self.credential_id).to_bytes(2, "big")
            + self.credential_id
            + self._cose_public_key()
        )
        attestation = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
        return {
            "id": b64(self.credential_id),
            "rawId": b64(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64(client_data),
                "attestationObject": b64(attestation),
                "transports": ["internal"],
            },
            "clientExtensionResults": {},
        }

    def assertion(self, options, *, origin=ORIGIN, flags=FLAG_UP | FLAG_UV, signing_key=None):
        self.sign_count += 1
        client_data = self._client_data("webauthn.get", options, origin)
        auth_data = (
            hashlib.sha256(options["rpId"].encode()).digest()
            + bytes([flags])
            + self.sign_count.to_bytes(4, "big")
        )
        signature = (signing_key or self.key).sign(
            auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256())
        )
        return {
            "id": b64(self.credential_id),
            "rawId": b64(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64(client_data),
                "authenticatorData": b64(auth_data),
                "signature": b64(signature),
            },
            "clientExtensionResults": {},
        }

    def stored_credential(self, user):
        """The row a successful registration would have stored for this authenticator."""
        return PasskeyCredential(
            id=uuid4(),
            user_id=user.id,
            credential_id=self.credential_id,
            public_key=self._cose_public_key(),
            sign_count=0,
            transports=["internal"],
        )


# -- Fixtures -----------------------------------------------------------------------


def make_user(role, name="Test User"):
    return User(
        id=uuid4(),
        email=f"{role.value}-{uuid4().hex[:6]}@unb.ca",
        full_name=name,
        role=role,
        is_active=True,
    )


def make_live_session(course, status=SessionStatus.ACTIVE):
    return ClassSession(
        id=uuid4(),
        course_id=course.id,
        status=status,
        actual_start=datetime.now(timezone.utc),
    )


class World:
    """A course taught by one professor with one enrolled student and an outsider."""

    def __init__(self):
        self.professor = make_user(UserRole.PROFESSOR, "Prof Ada")
        self.student = make_user(UserRole.STUDENT, "Sam Student")
        self.outsider = make_user(UserRole.STUDENT, "Olly Outsider")
        self.course = Course(id=uuid4(), code="ENGG 4000", title="Capstone", term="2026FALL")
        self.db = FakeSession(
            self.professor,
            self.student,
            self.outsider,
            self.course,
            CourseInstructor(course_id=self.course.id, professor_id=self.professor.id),
            Enrollment(course_id=self.course.id, student_id=self.student.id),
        )

    def add(self, *objects):
        self.db.objects.extend(objects)
        return objects[0] if len(objects) == 1 else objects


@pytest.fixture
def world(app):
    world = World()
    app.dependency_overrides[get_db_session] = lambda: world.db
    return world


# -- Professor: start / end / attendance ---------------------------------------------


def test_professor_starts_a_live_session(client, world):
    response = client.post(
        f"/courses/{world.course.id}/sessions", headers=auth_header(world.professor)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    assert body["course_id"] == str(world.course.id)
    assert body["started_at"]
    [live] = world.db.of(ClassSession)
    assert live.started_by == world.professor.id
    assert world.db.commits == 1


def test_professor_cannot_start_a_session_for_a_course_they_dont_teach(client, world):
    other = make_user(UserRole.PROFESSOR)
    world.add(other)

    response = client.post(f"/courses/{world.course.id}/sessions", headers=auth_header(other))

    assert response.status_code == 404
    assert world.db.of(ClassSession) == []


def test_student_cannot_start_a_session(client, world):
    response = client.post(
        f"/courses/{world.course.id}/sessions", headers=auth_header(world.student)
    )

    assert response.status_code == 403


def test_starting_a_second_live_session_is_rejected(client, world):
    world.add(make_live_session(world.course))

    response = client.post(
        f"/courses/{world.course.id}/sessions", headers=auth_header(world.professor)
    )

    assert response.status_code == 409


def test_concurrent_start_is_reported_as_a_conflict(client, world):
    world.db.commit_error = IntegrityError("INSERT", {}, Exception("duplicate key"))

    response = client.post(
        f"/courses/{world.course.id}/sessions", headers=auth_header(world.professor)
    )

    assert response.status_code == 409
    assert world.db.rolled_back is True


def test_professor_ends_a_live_session(client, world):
    live = world.add(make_live_session(world.course))

    response = client.post(f"/sessions/{live.id}/end", headers=auth_header(world.professor))

    assert response.status_code == 200
    assert response.json()["status"] == "ended"
    assert live.status == SessionStatus.ENDED
    assert live.actual_end is not None


def test_ending_an_ended_session_is_rejected(client, world):
    live = world.add(make_live_session(world.course, SessionStatus.ENDED))

    response = client.post(f"/sessions/{live.id}/end", headers=auth_header(world.professor))

    assert response.status_code == 409


def test_professor_sees_who_is_present_and_absent(client, world):
    live = world.add(make_live_session(world.course))
    late = make_user(UserRole.STUDENT, "Ann Absent")
    world.add(
        late,
        Enrollment(course_id=world.course.id, student_id=late.id),
        AttendanceRecord(
            id=uuid4(),
            session_id=live.id,
            student_id=world.student.id,
            status=AttendanceStatus.PRESENT,
            checked_in_at=datetime.now(timezone.utc),
        ),
    )

    response = client.get(f"/sessions/{live.id}/attendance", headers=auth_header(world.professor))

    assert response.status_code == 200
    body = response.json()
    assert body["enrolled_count"] == 2
    assert body["present_count"] == 1
    assert [(s["full_name"], s["status"]) for s in body["students"]] == [
        ("Ann Absent", "absent"),
        ("Sam Student", "present"),
    ]


def test_student_cannot_read_session_attendance(client, world):
    live = world.add(make_live_session(world.course))

    response = client.get(f"/sessions/{live.id}/attendance", headers=auth_header(world.student))

    assert response.status_code == 403


# -- Active session lookup -----------------------------------------------------------


def test_enrolled_student_sees_the_live_session(client, world):
    live = world.add(make_live_session(world.course))

    response = client.get(
        f"/courses/{world.course.id}/sessions/active", headers=auth_header(world.student)
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(live.id)
    assert response.json()["checked_in_at"] is None


def test_active_session_is_null_when_none_is_running(client, world):
    world.add(make_live_session(world.course, SessionStatus.ENDED))

    response = client.get(
        f"/courses/{world.course.id}/sessions/active", headers=auth_header(world.student)
    )

    assert response.status_code == 200
    assert response.json() is None


def test_unenrolled_student_cannot_see_the_course_session(client, world):
    world.add(make_live_session(world.course))

    response = client.get(
        f"/courses/{world.course.id}/sessions/active", headers=auth_header(world.outsider)
    )

    assert response.status_code == 404


# -- Passkey registration ------------------------------------------------------------


def register(client, world, authenticator, user=None, **kwargs):
    user = user or world.student
    options = client.post("/passkeys/register/options", headers=auth_header(user)).json()
    return client.post(
        "/passkeys/register",
        json={
            "challenge_id": options["challenge_id"],
            "credential": authenticator.register(options["options"], **kwargs),
        },
        headers=auth_header(user),
    )


def test_registration_options_require_user_verification(client, world):
    response = client.post("/passkeys/register/options", headers=auth_header(world.student))

    assert response.status_code == 200
    options = response.json()["options"]
    assert options["rp"]["id"] == RP_ID
    assert options["authenticatorSelection"]["userVerification"] == "required"
    assert base64url_to_bytes(options["user"]["id"]) == world.student.id.bytes
    [challenge] = world.db.of(WebAuthnChallenge)
    assert challenge.purpose == ChallengePurpose.PASSKEY_REGISTRATION
    assert b64(challenge.challenge) == options["challenge"]


def test_professor_cannot_register_a_passkey(client, world):
    response = client.post("/passkeys/register/options", headers=auth_header(world.professor))

    assert response.status_code == 403


def test_student_registers_a_passkey_and_only_its_public_key_is_stored(client, world):
    authenticator = SoftAuthenticator()

    response = register(client, world, authenticator)

    assert response.status_code == 201
    [credential] = world.db.of(PasskeyCredential)
    assert credential.user_id == world.student.id
    assert credential.credential_id == authenticator.credential_id
    assert credential.public_key == authenticator._cose_public_key()
    assert credential.transports == ["internal"]
    # The challenge is single-use.
    assert world.db.of(WebAuthnChallenge) == []


def test_registration_from_another_origin_is_rejected(client, world):
    response = register(client, world, SoftAuthenticator(), origin="https://evil.example")

    assert response.status_code == 400
    assert world.db.of(PasskeyCredential) == []
    assert world.db.of(WebAuthnChallenge) == []


def test_registration_without_user_verification_is_rejected(client, world):
    response = register(client, world, SoftAuthenticator(), flags=FLAG_UP | FLAG_AT)

    assert response.status_code == 400
    assert world.db.of(PasskeyCredential) == []


def test_expired_registration_challenge_is_rejected(client, world):
    authenticator = SoftAuthenticator()
    options = client.post("/passkeys/register/options", headers=auth_header(world.student)).json()
    world.db.of(WebAuthnChallenge)[0].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    response = client.post(
        "/passkeys/register",
        json={
            "challenge_id": options["challenge_id"],
            "credential": authenticator.register(options["options"]),
        },
        headers=auth_header(world.student),
    )

    assert response.status_code == 400
    assert world.db.of(PasskeyCredential) == []


def test_another_users_challenge_cannot_be_used(client, world):
    authenticator = SoftAuthenticator()
    options = client.post("/passkeys/register/options", headers=auth_header(world.student)).json()

    response = client.post(
        "/passkeys/register",
        json={
            "challenge_id": options["challenge_id"],
            "credential": authenticator.register(options["options"]),
        },
        headers=auth_header(world.outsider),
    )

    assert response.status_code == 400
    # The owner's challenge is untouched.
    assert len(world.db.of(WebAuthnChallenge)) == 1


# -- Passkey check-in ----------------------------------------------------------------


def with_passkey(world, user=None):
    authenticator = SoftAuthenticator()
    world.add(authenticator.stored_credential(user or world.student))
    return authenticator


def check_in(client, world, live, authenticator, user=None, **kwargs):
    user = user or world.student
    options = client.post(f"/sessions/{live.id}/check-in/options", headers=auth_header(user))
    assert options.status_code == 200, options.json()
    options = options.json()
    return client.post(
        f"/sessions/{live.id}/check-in",
        json={
            "challenge_id": options["challenge_id"],
            "credential": authenticator.assertion(options["options"], **kwargs),
        },
        headers=auth_header(user),
    )


def test_enrolled_student_checks_in_with_a_passkey(client, world):
    live = world.add(make_live_session(world.course))
    authenticator = with_passkey(world)

    response = check_in(client, world, live, authenticator)

    assert response.status_code == 200
    assert response.json()["status"] == "present"
    [record] = world.db.of(AttendanceRecord)
    assert record.student_id == world.student.id
    assert record.session_id == live.id
    assert record.status == AttendanceStatus.PRESENT
    [credential] = world.db.of(PasskeyCredential)
    assert record.passkey_credential_id == credential.id
    assert credential.sign_count == 1
    assert credential.last_used_at is not None
    assert world.db.of(WebAuthnChallenge) == []


def test_check_in_options_list_only_the_students_passkeys(client, world):
    live = world.add(make_live_session(world.course))
    mine = with_passkey(world)
    with_passkey(world, world.outsider)

    response = client.post(
        f"/sessions/{live.id}/check-in/options", headers=auth_header(world.student)
    )

    options = response.json()["options"]
    assert options["userVerification"] == "required"
    assert [c["id"] for c in options["allowCredentials"]] == [b64(mine.credential_id)]


def test_unenrolled_student_cannot_check_in(client, world):
    live = world.add(make_live_session(world.course))
    with_passkey(world, world.outsider)

    response = client.post(
        f"/sessions/{live.id}/check-in/options", headers=auth_header(world.outsider)
    )

    assert response.status_code == 404


def test_professor_cannot_check_in(client, world):
    live = world.add(make_live_session(world.course))

    response = client.post(
        f"/sessions/{live.id}/check-in/options", headers=auth_header(world.professor)
    )

    assert response.status_code == 403


def test_check_in_is_refused_once_the_session_has_ended(client, world):
    live = world.add(make_live_session(world.course, SessionStatus.ENDED))
    with_passkey(world)

    response = client.post(
        f"/sessions/{live.id}/check-in/options", headers=auth_header(world.student)
    )

    assert response.status_code == 409


def test_check_in_needs_a_registered_passkey(client, world):
    live = world.add(make_live_session(world.course))

    response = client.post(
        f"/sessions/{live.id}/check-in/options", headers=auth_header(world.student)
    )

    assert response.status_code == 409
    assert "passkey" in response.json()["detail"]


def test_session_ending_during_the_passkey_prompt_rejects_the_check_in(client, world):
    live = world.add(make_live_session(world.course))
    authenticator = with_passkey(world)
    options = client.post(
        f"/sessions/{live.id}/check-in/options", headers=auth_header(world.student)
    ).json()
    live.status = SessionStatus.ENDED

    response = client.post(
        f"/sessions/{live.id}/check-in",
        json={
            "challenge_id": options["challenge_id"],
            "credential": authenticator.assertion(options["options"]),
        },
        headers=auth_header(world.student),
    )

    assert response.status_code == 409
    assert world.db.of(AttendanceRecord) == []


def test_assertion_signed_by_another_key_is_rejected(client, world):
    live = world.add(make_live_session(world.course))
    authenticator = with_passkey(world)

    response = check_in(
        client, world, live, authenticator, signing_key=ec.generate_private_key(ec.SECP256R1())
    )

    assert response.status_code == 400
    assert world.db.of(AttendanceRecord) == []


def test_assertion_without_user_verification_is_rejected(client, world):
    live = world.add(make_live_session(world.course))
    authenticator = with_passkey(world)

    response = check_in(client, world, live, authenticator, flags=FLAG_UP)

    assert response.status_code == 400
    assert world.db.of(AttendanceRecord) == []


def test_assertion_from_another_origin_is_rejected(client, world):
    live = world.add(make_live_session(world.course))
    authenticator = with_passkey(world)

    response = check_in(client, world, live, authenticator, origin="https://evil.example")

    assert response.status_code == 400


def test_another_students_passkey_cannot_check_me_in(client, world):
    live = world.add(make_live_session(world.course))
    with_passkey(world)  # so options can be issued
    outsiders_key = with_passkey(world, world.outsider)

    response = check_in(client, world, live, outsiders_key)

    assert response.status_code == 400
    assert world.db.of(AttendanceRecord) == []


def test_a_check_in_challenge_cannot_be_replayed(client, world):
    live = world.add(make_live_session(world.course))
    authenticator = with_passkey(world)
    options = client.post(
        f"/sessions/{live.id}/check-in/options", headers=auth_header(world.student)
    ).json()
    bad = authenticator.assertion(options["options"], flags=FLAG_UP)  # fails verification
    good = authenticator.assertion(options["options"])
    body = lambda credential: {"challenge_id": options["challenge_id"], "credential": credential}

    first = client.post(
        f"/sessions/{live.id}/check-in", json=body(bad), headers=auth_header(world.student)
    )
    second = client.post(
        f"/sessions/{live.id}/check-in", json=body(good), headers=auth_header(world.student)
    )

    assert first.status_code == 400
    assert second.status_code == 400
    assert world.db.of(AttendanceRecord) == []


def test_challenge_for_one_session_cannot_check_in_to_another(client, world):
    first = world.add(make_live_session(world.course))
    other_course = Course(id=uuid4(), code="ENGG 4001", title="Other", term="2026FALL")
    second = make_live_session(other_course)
    world.add(other_course, second, Enrollment(course_id=other_course.id, student_id=world.student.id))
    authenticator = with_passkey(world)
    options = client.post(
        f"/sessions/{first.id}/check-in/options", headers=auth_header(world.student)
    ).json()

    response = client.post(
        f"/sessions/{second.id}/check-in",
        json={
            "challenge_id": options["challenge_id"],
            "credential": authenticator.assertion(options["options"]),
        },
        headers=auth_header(world.student),
    )

    assert response.status_code == 400
    assert world.db.of(AttendanceRecord) == []


def test_student_cannot_check_in_twice(client, world):
    live = world.add(make_live_session(world.course))
    authenticator = with_passkey(world)
    assert check_in(client, world, live, authenticator).status_code == 200

    response = client.post(
        f"/sessions/{live.id}/check-in/options", headers=auth_header(world.student)
    )

    assert response.status_code == 409
    active = client.get(
        f"/courses/{world.course.id}/sessions/active", headers=auth_header(world.student)
    )
    assert active.json()["checked_in_at"] is not None
