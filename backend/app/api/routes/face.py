from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session
from app.models.student_face_embedding import StudentFaceEmbedding
from app.models.user import User, UserRole
from app.services.face_embedding import MODEL, compare_face_embeddings, extract_face_embedding

router = APIRouter(prefix="/face", tags=["Face verification"])


@router.post("/verify")
def verify_my_face(
    selfie: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only students have an enrolled face.")

    enrollment = session.get(StudentFaceEmbedding, current_user.id)
    if enrollment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No face enrolled for your account yet.")

    if enrollment.model_name != MODEL:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Incompatible face embedding model.")

    selfie_embedding = extract_face_embedding(selfie)
    return compare_face_embeddings(enrollment.embedding, selfie_embedding)
