from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class StudentFaceEmbedding(Base):
    __tablename__ = "student_face_embeddings"

    student_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(512),
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Facenet512",
        server_default="Facenet512",
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )