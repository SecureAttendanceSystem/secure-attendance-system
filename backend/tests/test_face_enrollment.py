from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes import face_verification
from app.models.student_face_embedding import StudentFaceEmbedding


class EnrollmentSession:
    def __init__(self, saved):
        self.saved = saved
        self.added = []
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def execute(self, *_args):
        return SimpleNamespace(scalar_one_or_none=lambda: "student")

    def get(self, model, student_id):
        assert model is StudentFaceEmbedding
        assert self.saved is None or self.saved.student_id == student_id
        return self.saved

    def add(self, enrollment):
        self.added.append(enrollment)

    def commit(self):
        self.committed = True


@pytest.mark.parametrize("already_enrolled", [False, True])
def test_enroll_creates_or_replaces_face(app, client, monkeypatch, already_enrolled):
    app.state.settings.environment = "development"
    student_id = uuid4()
    saved = StudentFaceEmbedding(student_id=student_id, embedding=[0.1] * 512, model_name="OldModel") if already_enrolled else None
    session = EnrollmentSession(saved)
    monkeypatch.setattr(face_verification, "Session", lambda engine: session)
    monkeypatch.setattr(face_verification, "extract_face_embedding", lambda photo: [0.2] * 512)

    response = client.post("/face-spike/enroll-test", data={"student_id": str(student_id)}, files={"reference": ("face.jpg", b"photo", "image/jpeg")})

    assert response.status_code == 201
    assert session.committed
    enrollment = saved if already_enrolled else session.added[0]
    assert enrollment.embedding == [0.2] * 512
    assert enrollment.model_name == face_verification.MODEL
    assert len(session.added) == (0 if already_enrolled else 1)


def test_invalid_replacement_preserves_existing_face(app, client, monkeypatch):
    app.state.settings.environment = "development"
    student_id = uuid4()
    saved = StudentFaceEmbedding(student_id=student_id, embedding=[0.1] * 512, model_name=face_verification.MODEL)
    session = EnrollmentSession(saved)
    monkeypatch.setattr(face_verification, "Session", lambda engine: session)

    def invalid_photo(photo):
        raise HTTPException(422, "Invalid photo")

    monkeypatch.setattr(face_verification, "extract_face_embedding", invalid_photo)
    response = client.post("/face-spike/enroll-test", data={"student_id": str(student_id)}, files={"reference": ("face.jpg", b"invalid", "image/jpeg")})

    assert response.status_code == 422
    assert saved.embedding == [0.1] * 512
    assert not session.committed


@pytest.mark.parametrize("endpoint", ["compare", "enroll-test", "verify-test"])
def test_spike_endpoints_are_unavailable_in_production(app, client, endpoint):
    app.state.settings.environment = "production"
    response = client.post(
        f"/face-spike/{endpoint}",
        data={"student_id": str(uuid4())},
        files={name: ("face.jpg", b"photo", "image/jpeg") for name in ("reference", "selfie")},
    )
    assert response.status_code == 404
