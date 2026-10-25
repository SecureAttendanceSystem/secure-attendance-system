from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import DevicePlatform, enum_column


class RegisteredDevice(Base):
    __tablename__ = "registered_devices"
    __table_args__ = (
        # One active device per user, and one active owner per device.
        # "Active" means revoked_at IS NULL, so revoked history is kept.
        Index(
            "uq_registered_devices_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
        Index(
            "uq_registered_devices_active_identifier",
            "device_identifier",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    device_identifier: Mapped[str] = mapped_column(String(255))
    platform: Mapped[DevicePlatform] = mapped_column(
        enum_column(DevicePlatform, "device_platform")
    )
    device_label: Mapped[str | None] = mapped_column(String(100))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    approved_by: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
