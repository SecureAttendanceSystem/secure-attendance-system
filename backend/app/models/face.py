from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class FaceEnrollment(Base):
    """Stores only the face provider's reference ID, never the image itself."""

    __tablename__ = "face_enrollments"
    __table_args__ = (
        # One active face profile per account; revoked rows are kept as history.
        Index(
            "uq_face_enrollments_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(50))  # e.g. "aws_rekognition"
    provider_face_id: Mapped[str] = mapped_column(String(255))
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    approved_by: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
