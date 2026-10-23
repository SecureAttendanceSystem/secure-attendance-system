from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Float, Integer, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("building", "room_number", name="uq_rooms_building_room_number"),
        # The naming convention turns this into ck_rooms_geofence_positive.
        CheckConstraint("geofence_radius_m > 0", name="geofence_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    building: Mapped[str] = mapped_column(String(100))
    room_number: Mapped[str] = mapped_column(String(32))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    geofence_radius_m: Mapped[int] = mapped_column(
        Integer, default=50, server_default=text("50")
    )
    ble_beacon_uuid: Mapped[str | None] = mapped_column(String(64))
