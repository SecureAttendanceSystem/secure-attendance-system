from io import BytesIO
from uuid import uuid4

from app.api.deps import get_db_session
from app.models.student_face_embedding import StudentFaceEmbedding
from app.models.user import User, UserRole
from app.security.tokens import create_access_token
from app.services import face_embedding


class FakeSession:
    def __init__(self, user, enrollment=None):
        self.user = user
        self.enrollment = enrollment

    def get(self, model, pk):
        if model is StudentFaceEmbedding:
            return self.enrollment
        if model is User and pk == self.user.id:
            return self.user
        return None


def make_user(role=UserRole.STUDENT, **overrides):
    defaults = dict(
        id=uuid4(),
        email="student@unb.ca",
        full_name="Pat Student",
        password_hash="unused",
        role=role,
        is_active=True,
    )
    defaults.update(overrides)
    return User(**defaults)


def auth_header(app, settings, user):
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    return {"Authorization": f"Bearer {token}"}


def selfie_file():
    return {"selfie": ("selfie.jpg", BytesIO(b"not-a-real-image"), "image/jpeg")}


def test_verify_requires_authentication(client):
    response = client.post("/face/verify", files=selfie_file())
    assert response.status_code == 401


def test_verify_rejects_a_non_student(app, client, settings):
    professor = make_user(role=UserRole.PROFESSOR)
    app.dependency_overrides[get_db_session] = lambda: FakeSession(professor)

    response = client.post(
        "/face/verify",
        files=selfie_file(),
        headers=auth_header(app, settings, professor),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Only students have an enrolled face."}


def test_verify_rejects_when_no_face_is_enrolled(app, client, settings):
    student = make_user()
    app.dependency_overrides[get_db_session] = lambda: FakeSession(student, enrollment=None)

    response = client.post(
        "/face/verify",
        files=selfie_file(),
        headers=auth_header(app, settings, student),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "No face enrolled for your account yet."}


def test_verify_rejects_an_incompatible_embedding_model(app, client, settings):
    student = make_user()
    enrollment = StudentFaceEmbedding(
        student_id=student.id, embedding=[0.0] * 512, model_name="OldModel"
    )
    app.dependency_overrides[get_db_session] = lambda: FakeSession(student, enrollment=enrollment)

    response = client.post(
        "/face/verify",
        files=selfie_file(),
        headers=auth_header(app, settings, student),
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Incompatible face embedding model."}


def test_verify_compares_against_the_students_own_enrollment(app, client, settings, monkeypatch):
    student = make_user()
    enrollment = StudentFaceEmbedding(
        student_id=student.id, embedding=[0.1, 0.2], model_name=face_embedding.MODEL
    )
    app.dependency_overrides[get_db_session] = lambda: FakeSession(student, enrollment=enrollment)

    seen = {}

    def fake_extract(_photo):
        return [0.3, 0.4]

    def fake_compare(reference, candidate):
        seen["reference"] = reference
        seen["candidate"] = candidate
        return {"matched": True, "distance": 0.1, "threshold": 0.3}

    monkeypatch.setattr("app.api.routes.face.extract_face_embedding", fake_extract)
    monkeypatch.setattr("app.api.routes.face.compare_face_embeddings", fake_compare)

    response = client.post(
        "/face/verify",
        files=selfie_file(),
        headers=auth_header(app, settings, student),
    )

    assert response.status_code == 200
    assert response.json() == {"matched": True, "distance": 0.1, "threshold": 0.3}
    # The endpoint must compare against the caller's own enrollment, never a
    # student_id supplied by the client.
    assert seen["reference"] == enrollment.embedding
    assert seen["candidate"] == [0.3, 0.4]
