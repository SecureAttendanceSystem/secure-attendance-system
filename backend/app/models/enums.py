"""Enums shared by the attendance models.

Stored the same way as UserRole: as VARCHAR plus a CHECK constraint
(native_enum=False), so no PostgreSQL enum types are created.
"""

from enum import Enum

from sqlalchemy import Enum as SQLEnum


class DevicePlatform(str, Enum):
    IOS = "ios"
    ANDROID = "android"


class SessionStatus(str, Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"


class CheckKind(str, Enum):
    UNIVERSITY_AUTH = "university_auth"
    DEVICE = "device"
    GPS = "gps"
    BLE = "ble"
    FACE = "face"
    QR = "qr"


def enum_column(enum_class: type[Enum], name: str) -> SQLEnum:
    """Build the column type with the same options user.py uses for UserRole.

    Returns a fresh instance each call, because a SQLAlchemy Enum type binds
    to the table it is first attached to.
    """
    return SQLEnum(
        enum_class,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        name=name,
        validate_strings=True,
    )
