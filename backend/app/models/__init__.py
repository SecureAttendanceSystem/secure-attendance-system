"""Import each model here so Alembic discovers its table metadata.

All models should inherit from app.database.base.Base.
"""

from app.models.attendance import AttendanceRecord, CheckResult
from app.models.audit_log import AuditLog
from app.models.change_request import ChangeRequest
from app.models.class_session import ClassSession, SessionRequiredCheck
from app.models.course import Course, CourseInstructor, Enrollment
from app.models.device import RegisteredDevice
from app.models.enums import (
    AttendanceStatus,
    ChallengePurpose,
    ChangeType,
    CheckKind,
    CheckOutcome,
    DevicePlatform,
    RequestStatus,
    SessionStatus,
)
from app.models.passkey import PasskeyCredential, WebAuthnChallenge
from app.models.room import Room
from app.models.student_face_embedding import StudentFaceEmbedding
from app.models.user import User, UserRole

__all__ = [
    "AttendanceRecord",
    "AttendanceStatus",
    "AuditLog",
    "ChallengePurpose",
    "ChangeRequest",
    "ChangeType",
    "CheckKind",
    "CheckOutcome",
    "CheckResult",
    "ClassSession",
    "Course",
    "CourseInstructor",
    "DevicePlatform",
    "Enrollment",
    "PasskeyCredential",
    "RegisteredDevice",
    "RequestStatus",
    "Room",
    "SessionRequiredCheck",
    "SessionStatus",
    "StudentFaceEmbedding",
    "User",
    "UserRole",
    "WebAuthnChallenge",
]
