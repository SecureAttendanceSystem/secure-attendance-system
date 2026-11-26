from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Text, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import (
    AttendanceStatus,
    CheckKind,
    CheckOutcome,
    enum_column,
)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "student_id", name="uq_attendance_records_session_student"
        ),
        Index("ix_attendance_records_student_id", "student_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("class_sessions.id"))
    student_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    status: Mapped[AttendanceStatus] = mapped_column(
        enum_column(AttendanceStatus, "attendance_status")
    )
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    device_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("registered_devices.id")
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    review_note: Mapped[str | None] = mapped_column(Text)


class CheckResult(Base):
    """Outcome of one check (GPS, BLE, face, ...) within a check-in attempt."""

    __tablename__ = "check_results"
    __table_args__ = (Index("ix_check_results_attendance_id", "attendance_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    attendance_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("attendance_records.id", ondelete="CASCADE")
    )
    check_kind: Mapped[CheckKind] = mapped_column(enum_column(CheckKind, "check_kind"))
    outcome: Mapped[CheckOutcome] = mapped_column(
        enum_column(CheckOutcome, "check_outcome")
    )
    # Free-form evidence, e.g. {"distance_m": 12.4} or {"confidence": 97.1}
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
