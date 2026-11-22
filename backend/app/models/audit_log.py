from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AuditLog(Base):
    """Append-only record of sensitive actions.

    In production, grant the application's database role INSERT and SELECT
    only on this table (no UPDATE or DELETE).
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor_id_created_at", "actor_id", "created_at"),
        Index("ix_audit_logs_entity_type_entity_id", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))  # e.g. "device.approve"
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
