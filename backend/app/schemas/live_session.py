from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import SessionStatus


class LiveSessionPublic(BaseModel):
    id: UUID
    course_id: UUID
    status: SessionStatus
    started_at: datetime | None
    ended_at: datetime | None
    # Only filled in for a student: when they checked in to this session.
    checked_in_at: datetime | None = None


class AttendanceEntry(BaseModel):
    student_id: UUID
    full_name: str
    email: str
    status: Literal["present", "absent"]
    checked_in_at: datetime | None


class SessionAttendance(BaseModel):
    session: LiveSessionPublic
    enrolled_count: int
    present_count: int
    students: list[AttendanceEntry]


class CheckInResult(BaseModel):
    session_id: UUID
    status: Literal["present"]
    checked_in_at: datetime


class CeremonyOptions(BaseModel):
    """WebAuthn options for the browser, plus the ID of the challenge they carry."""

    challenge_id: UUID
    # PublicKeyCredentialCreationOptionsJSON / ...RequestOptionsJSON, passed
    # straight to navigator.credentials via @simplewebauthn/browser.
    options: dict[str, Any]


class CeremonyResponse(BaseModel):
    challenge_id: UUID
    # The browser's PublicKeyCredential serialized as JSON (base64url fields).
    credential: dict[str, Any]


class PasskeyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime | None
    last_used_at: datetime | None
    transports: list[str] | None
