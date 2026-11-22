from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import CheckKind, SessionStatus, enum_column


class ClassSession(Base):
    __tablename__ = "class_sessions"
    __table_args__ = (
        # The naming convention turns this into ck_class_sessions_time_order.
        CheckConstraint("scheduled_end > scheduled_start", name="time_order"),
        Index("ix_class_sessions_course_id_scheduled_start", "course_id", "scheduled_start"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("courses.id"))
    room_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("rooms.id"))
    started_by: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[SessionStatus] = mapped_column(
        enum_column(SessionStatus, "session_status"),
        default=SessionStatus.SCHEDULED,
        server_default=SessionStatus.SCHEDULED.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SessionRequiredCheck(Base):
    """Which checks a session requires; this is what makes checks vary per session."""

    __tablename__ = "session_required_checks"

    session_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("class_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    check_kind: Mapped[CheckKind] = mapped_column(
        enum_column(CheckKind, "check_kind"), primary_key=True
    )
