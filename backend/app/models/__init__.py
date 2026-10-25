"""Import each model here so Alembic discovers its table metadata.

All models should inherit from app.database.base.Base.
"""

from app.models.attendance import AttendanceRecord, CheckResult
from app.models.class_session import ClassSession, SessionRequiredCheck
from app.models.course import Course, CourseInstructor, Enrollment
from app.models.device import RegisteredDevice
from app.models.enums import (
    AttendanceStatus,
    CheckKind,
    CheckOutcome,
    DevicePlatform,
    SessionStatus,
)
from app.models.face import FaceEnrollment
from app.models.room import Room
from app.models.user import User, UserRole

__all__ = [
    "AttendanceRecord",
    "AttendanceStatus",
    "CheckKind",
    "CheckOutcome",
    "CheckResult",
    "ClassSession",
    "Course",
    "CourseInstructor",
    "DevicePlatform",
    "Enrollment",
    "FaceEnrollment",
    "RegisteredDevice",
    "Room",
    "SessionRequiredCheck",
    "SessionStatus",
    "User",
    "UserRole",
]
