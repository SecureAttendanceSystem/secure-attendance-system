import cv2
import numpy as np
from deepface import DeepFace
from fastapi import APIRouter, HTTPException, Request, UploadFile
from uuid import UUID
from fastapi import File, Form
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.student_face_embedding import StudentFaceEmbedding

router = APIRouter(prefix="/face-spike", tags=["Face spike"])

MODEL = "Facenet512"
MAX_BYTES = 5 * 1024 * 1024  # 5 MB per photo


def get_embedding(photo: UploadFile) -> list[float]:
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
        )
    except ValueError:
        raise HTTPException(
            422, "Could not process the face. Try a clearer photo."
        ) from None

    if len(faces) != 1:
        raise HTTPException(422, "The photo must contain exactly one face.")

    return faces[0]["embedding"]


@router.post("/compare")
def compare_faces(
    request: Request,
    reference: UploadFile,
    selfie: UploadFile,
):
    # This temporary endpoint has no login protection.
    if request.app.state.settings.environment != "development":
        raise HTTPException(404, "Not found")

    result = DeepFace.verify(
        img1_path=get_embedding(reference),
        img2_path=get_embedding(selfie),
        model_name=MODEL,
        distance_metric="cosine",
        silent=True,
    )

    return {
        "matched": bool(result["verified"]),
        "distance": float(result["distance"]),
        "threshold": float(result["threshold"]),
    }


@router.post("/enroll-test", status_code=201)
def enroll_test(
    request: Request,
    student_id: UUID = Form(...),
    reference: UploadFile = File(...),
):
    # Never expose this endpoint outside development.
    if request.app.state.settings.environment != "development":
        raise HTTPException(404, "Not found")

    engine = request.app.state.database_engine

    with Session(engine) as session:
        role = session.execute(
            text(
                "SELECT role FROM public.users "
                "WHERE id = :student_id"
            ),
            {"student_id": str(student_id)},
        ).scalar_one_or_none()

        if role is None:
            raise HTTPException(404, "Student not found")

        if role != "student":
            raise HTTPException(403, "User is not a student")

        if session.get(StudentFaceEmbedding, student_id):
            raise HTTPException(409, "Face already enrolled")

        embedding = get_embedding(reference)

        session.add(
            StudentFaceEmbedding(
                student_id=student_id,
                embedding=embedding,
                model_name=MODEL,
            )
        )

        session.commit()

    return {
        "enrolled": True,
        "student_id": str(student_id),
        "model": MODEL,
    }


@router.post("/verify-test")
def verify_test(
    request: Request,
    student_id: UUID = Form(...),
    selfie: UploadFile = File(...),
):
    # Development only
    if request.app.state.settings.environment != "development":
        raise HTTPException(404, "Not found")

    engine = request.app.state.database_engine

    with Session(engine) as session:
        saved = session.get(
            StudentFaceEmbedding,
            student_id,
        )

        if saved is None:
            raise HTTPException(
                404, "No face enrolled for this student."
            )

        if saved.model_name != MODEL:
            raise HTTPException(
                422, "Incompatible face embedding model."
            )

        reference_embedding = saved.embedding

    # Generate embedding from new selfie
    selfie_embedding = get_embedding(selfie)

    # Compare against stored embedding
    result = DeepFace.verify(
        img1_path=reference_embedding,
        img2_path=selfie_embedding,
        model_name=MODEL,
        distance_metric="cosine",
        silent=True,
    )

    return {
        "matched": bool(result["verified"]),
        "distance": float(result["distance"]),
        "threshold": float(result["threshold"]),
    }
