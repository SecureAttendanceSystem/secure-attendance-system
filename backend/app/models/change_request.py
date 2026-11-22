from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import ChangeType, DevicePlatform, RequestStatus, enum_column


class ChangeRequest(Base):
    """A student's request to change their registered device or face profile."""

    __tablename__ = "change_requests"
    __table_args__ = (Index("ix_change_requests_status", "status"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    type: Mapped[ChangeType] = mapped_column(enum_column(ChangeType, "change_type"))
    reason: Mapped[str | None] = mapped_column(Text)
    new_device_identifier: Mapped[str | None] = mapped_column(String(255))
    new_device_platform: Mapped[DevicePlatform | None] = mapped_column(
        enum_column(DevicePlatform, "device_platform")
    )
    status: Mapped[RequestStatus] = mapped_column(
        enum_column(RequestStatus, "request_status"),
        default=RequestStatus.PENDING,
        server_default=RequestStatus.PENDING.value,
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
