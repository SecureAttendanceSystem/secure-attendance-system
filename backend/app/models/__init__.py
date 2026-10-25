"""Import each model here so Alembic discovers its table metadata.

All models should inherit from app.database.base.Base.
"""

from app.models.class_session import ClassSession, SessionRequiredCheck
from app.models.course import Course, CourseInstructor, Enrollment
from app.models.device import RegisteredDevice
from app.models.enums import CheckKind, DevicePlatform, SessionStatus
from app.models.face import FaceEnrollment
from app.models.room import Room
from app.models.user import User, UserRole

__all__ = [
    "CheckKind",
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
