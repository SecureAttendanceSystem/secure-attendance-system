import cv2
import numpy as np
from deepface import DeepFace
from fastapi import HTTPException, UploadFile

MODEL = "Facenet512"
MAX_BYTES = 5 * 1024 * 1024  # 5 MB per photo


def extract_face_embedding(photo: UploadFile) -> list[float]:
    data = photo.file.read(MAX_BYTES + 1)

    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Photo must be smaller than 5 MB.")

    if not data:
        raise HTTPException(422, "The uploaded photo is empty.")

    image = cv2.imdecode(
        np.frombuffer(data, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise HTTPException(422, "Could not read the photo.")

    try:
        faces = DeepFace.represent(
            img_path=image,
            model_name=MODEL,
            enforce_detection=True,
            anti_spoofing=True,
        )
    except ValueError:
        raise HTTPException(
            422, "Could not process the face. Try a clearer photo."
        ) from None

    if len(faces) != 1:
        raise HTTPException(422, "The photo must contain exactly one face.")

    return faces[0]["embedding"]


def compare_face_embeddings(reference: list[float], candidate: list[float]) -> dict:
    result = DeepFace.verify(
        # Some pgvector versions return NumPy arrays; DeepFace interprets
        # arrays as images, and only lists as precomputed embeddings.
        img1_path=[float(value) for value in reference],
        img2_path=[float(value) for value in candidate],
        model_name=MODEL,
        distance_metric="cosine",
        silent=True,
    )
    return {
        "matched": bool(result["verified"]),
        "distance": float(result["distance"]),
        "threshold": float(result["threshold"]),
    }
