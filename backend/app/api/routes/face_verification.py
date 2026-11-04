from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.student_face_embedding import StudentFaceEmbedding
from app.services.face_embedding import (
    MODEL,
    compare_face_embeddings,
    extract_face_embedding,
)

router = APIRouter(prefix="/face-spike", tags=["Face spike"])


@router.post("/compare")
def compare_faces(
    request: Request,
    reference: UploadFile,
    selfie: UploadFile,
):
    # This temporary endpoint has no login protection.
    if request.app.state.settings.environment != "development":
        raise HTTPException(404, "Not found")

    return compare_face_embeddings(
        extract_face_embedding(reference),
        extract_face_embedding(selfie),
    )


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

        saved = session.get(StudentFaceEmbedding, student_id)
        embedding = extract_face_embedding(reference)

        if saved is not None:
            saved.embedding = embedding
            saved.model_name = MODEL
        else:
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

    selfie_embedding = extract_face_embedding(selfie)

    return compare_face_embeddings(reference_embedding, selfie_embedding)
