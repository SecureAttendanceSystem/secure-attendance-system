from io import BytesIO

import cv2
import numpy as np
import pytest
from fastapi import HTTPException, UploadFile

from app.services import face_embedding
from evaluation.evaluate_face_verification import evaluate_image


def photo(data):
    return UploadFile(filename="face.jpg", file=BytesIO(data))


def encoded_photo():
    ok, data = cv2.imencode(".jpg", np.zeros((16, 16, 3), dtype=np.uint8))
    assert ok
    return data.tobytes()


@pytest.mark.parametrize("data, status", [(b"", 422), (b"not an image", 422), (b"x" * (face_embedding.MAX_BYTES + 1), 413)])
def test_invalid_uploads_are_rejected_before_inference(monkeypatch, data, status):
    def unexpected_inference(**kwargs):
        pytest.fail("Invalid uploads must not reach face inference")

    monkeypatch.setattr(face_embedding.DeepFace, "represent", unexpected_inference)
    with pytest.raises(HTTPException) as error:
        face_embedding.extract_face_embedding(photo(data))
    assert error.value.status_code == status


def test_spoof_check_runs_on_the_image_before_embedding(monkeypatch):
    def reject_spoof(**kwargs):
        assert isinstance(kwargs["img_path"], np.ndarray)
        assert kwargs["anti_spoofing"] is True
        raise ValueError("Spoof detected")

    monkeypatch.setattr(face_embedding.DeepFace, "represent", reject_spoof)
    with pytest.raises(HTTPException) as error:
        face_embedding.extract_face_embedding(photo(encoded_photo()))
    assert error.value.status_code == 422


@pytest.mark.parametrize("face_count", [0, 2])
def test_requires_exactly_one_face(monkeypatch, face_count):
    monkeypatch.setattr(face_embedding.DeepFace, "represent", lambda **kwargs: [{"embedding": [0.1] * 512}] * face_count)
    with pytest.raises(HTTPException, match="exactly one face"):
        face_embedding.extract_face_embedding(photo(encoded_photo()))


def test_database_arrays_are_passed_as_embeddings_not_images(monkeypatch):
    def verify(**kwargs):
        assert isinstance(kwargs["img1_path"], list)
        assert isinstance(kwargs["img2_path"], list)
        assert all(type(value) is float for value in kwargs["img1_path"])
        assert kwargs["img1_path"] == [0.25] * 512
        return {"verified": np.bool_(True), "distance": np.float32(0.1), "threshold": 0.3}

    monkeypatch.setattr(face_embedding.DeepFace, "verify", verify)
    result = face_embedding.compare_face_embeddings(np.full(512, 0.25, dtype=np.float32), [0.5] * 512)
    assert result["matched"] is True
    assert type(result["distance"]) is float


def test_evaluation_uses_shared_extraction_and_comparison(tmp_path, monkeypatch):
    path = tmp_path / "selfie.jpg"
    path.write_bytes(encoded_photo())
    monkeypatch.setattr(face_embedding.DeepFace, "represent", lambda **kwargs: [{"embedding": [0.1] * 512}])
    monkeypatch.setattr(face_embedding.DeepFace, "verify", lambda **kwargs: {"verified": True, "distance": 0.1, "threshold": 0.3})
    row = evaluate_image(path, "Yes", [0.1] * 512)
    assert row["Result"] == "TP"
    assert row["Error detail"] == ""
