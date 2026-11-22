"""Live attendance sessions and passkey check-in.

A professor starts a live session for a course they teach; while it is
active, each enrolled student can check in once by signing a fresh server
challenge with a passkey registered to their account.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session, require_role
from app.api.routes.courses import can_view_course, require_roster_access
from app.models.attendance import AttendanceRecord
from app.models.class_session import ClassSession
from app.models.course import Course, CourseInstructor, Enrollment
from app.models.enums import AttendanceStatus, ChallengePurpose, SessionStatus
from app.models.passkey import PasskeyCredential
from app.models.user import User, UserRole
from app.schemas.live_session import (
    AttendanceEntry,
    CeremonyOptions,
    CeremonyResponse,
    CheckInResult,
    LiveSessionPublic,
    SessionAttendance,
)
from app.services import passkeys
from app.services.passkeys import PasskeyVerificationError, utcnow

router = APIRouter(tags=["Live sessions"])

DbSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Professor = Annotated[User, Depends(require_role(UserRole.PROFESSOR))]
Student = Annotated[User, Depends(require_role(UserRole.STUDENT))]


def to_public(live: ClassSession, checked_in_at=None) -> LiveSessionPublic:
    return LiveSessionPublic(
        id=live.id,
        course_id=live.course_id,
        status=live.status,
        started_at=live.actual_start,
        ended_at=live.actual_end,
        checked_in_at=checked_in_at,
    )


def find_active_session(db: Session, course_id: UUID) -> ClassSession | None:
    return db.scalars(
        select(ClassSession).where(
            ClassSession.course_id == course_id,
            ClassSession.status == SessionStatus.ACTIVE,
        )
    ).first()


def find_attendance(db: Session, session_id: UUID, student_id: UUID) -> AttendanceRecord | None:
    return db.scalars(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == student_id,
        )
    ).first()


def require_teaching(db: Session, user: User, course_id: UUID) -> None:
    """Only a course's own professors run its sessions; others get 404 so IDs can't be probed."""
    if db.get(Course, course_id) is None or db.get(CourseInstructor, (course_id, user.id)) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")


def get_visible_session(db: Session, user: User, session_id: UUID) -> ClassSession:
    live = db.get(ClassSession, session_id)
    if live is None or not can_view_course(db, user, live.course_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return live


def require_open(live: ClassSession) -> None:
    if live.status != SessionStatus.ACTIVE:
        raise HTTPException(status.HTTP_409_CONFLICT, "This session is not open for check-in")


# -- Professor ------------------------------------------------------------------


@router.post(
    "/courses/{course_id}/sessions",
    response_model=LiveSessionPublic,
    status_code=status.HTTP_201_CREATED,
)
def start_session(course_id: UUID, db: DbSession, professor: Professor) -> LiveSessionPublic:
    require_teaching(db, professor, course_id)
    if find_active_session(db, course_id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A session is already live for this course")

    live = ClassSession(
        course_id=course_id,
        started_by=professor.id,
        actual_start=utcnow(),
        status=SessionStatus.ACTIVE,
    )
    db.add(live)
    try:
        db.commit()
    except IntegrityError:
        # Another request started a session at the same moment (unique partial index).
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A session is already live for this course"
        ) from None
    db.refresh(live)
    return to_public(live)


@router.post("/sessions/{session_id}/end", response_model=LiveSessionPublic)
def end_session(session_id: UUID, db: DbSession, professor: Professor) -> LiveSessionPublic:
    live = db.get(ClassSession, session_id)
    if live is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    require_teaching(db, professor, live.course_id)
    require_open(live)

    live.status = SessionStatus.ENDED
    live.actual_end = utcnow()
    db.commit()
    db.refresh(live)
    return to_public(live)


@router.get("/sessions/{session_id}/attendance", response_model=SessionAttendance)
def read_attendance(session_id: UUID, db: DbSession, user: CurrentUser) -> SessionAttendance:
    live = db.get(ClassSession, session_id)
    if live is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    require_roster_access(db, user, live.course_id)

    student_ids = [
        enrollment.student_id
        for enrollment in db.scalars(
            select(Enrollment).where(Enrollment.course_id == live.course_id)
        ).all()
    ]
    students = (
        db.scalars(select(User).where(User.id.in_(student_ids))).all() if student_ids else []
    )
    records = {
        record.student_id: record
        for record in db.scalars(
            select(AttendanceRecord).where(AttendanceRecord.session_id == live.id)
        ).all()
    }

    entries = []
    for student in sorted(students, key=lambda s: (s.full_name.lower(), s.email)):
        record = records.get(student.id)
        present = record is not None and record.status == AttendanceStatus.PRESENT
        entries.append(
            AttendanceEntry(
                student_id=student.id,
                full_name=student.full_name,
                email=student.email,
                status="present" if present else "absent",
                checked_in_at=record.checked_in_at if present else None,
            )
        )
    return SessionAttendance(
        session=to_public(live),
        enrolled_count=len(entries),
        present_count=sum(entry.status == "present" for entry in entries),
        students=entries,
    )


# -- Professor and student --------------------------------------------------------


@router.get("/courses/{course_id}/sessions/active", response_model=LiveSessionPublic | None)
def read_active_session(
    course_id: UUID, db: DbSession, user: CurrentUser
) -> LiveSessionPublic | None:
    """The course's live session, or null when none is running."""
    if db.get(Course, course_id) is None or not can_view_course(db, user, course_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    live = find_active_session(db, course_id)
    if live is None:
        return None
    checked_in_at = None
    if user.role == UserRole.STUDENT:
        record = find_attendance(db, live.id, user.id)
        checked_in_at = record.checked_in_at if record is not None else None
    return to_public(live, checked_in_at)


# -- Student check-in -------------------------------------------------------------


@router.post("/sessions/{session_id}/check-in/options", response_model=CeremonyOptions)
def check_in_options(
    session_id: UUID, request: Request, db: DbSession, student: Student
) -> CeremonyOptions:
    live = get_visible_session(db, student, session_id)
    require_open(live)
    if find_attendance(db, live.id, student.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already checked in")

    credentials = db.scalars(
        select(PasskeyCredential).where(PasskeyCredential.user_id == student.id)
    ).all()
    if not credentials:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Set up a passkey on this device before checking in"
        )

    options, challenge = passkeys.authentication_options(request.app.state.settings, credentials)
    row = passkeys.issue_challenge(
        db, student, ChallengePurpose.CHECK_IN, challenge, class_session_id=live.id
    )
    return CeremonyOptions(challenge_id=row.id, options=options)


@router.post("/sessions/{session_id}/check-in", response_model=CheckInResult)
def check_in(
    session_id: UUID,
    payload: CeremonyResponse,
    request: Request,
    db: DbSession,
    student: Student,
) -> CheckInResult:
    live = get_visible_session(db, student, session_id)
    challenge = passkeys.consume_challenge(
        db, payload.challenge_id, student, ChallengePurpose.CHECK_IN, class_session_id=live.id
    )
    # Re-check after the passkey prompt: the professor may have ended the session meanwhile.
    db.refresh(live)
    require_open(live)
    if find_attendance(db, live.id, student.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already checked in")

    try:
        credential_id = passkeys.credential_id_of(payload.credential)
    except PasskeyVerificationError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passkey verification failed") from None
    credential = db.scalars(
        select(PasskeyCredential).where(
            PasskeyCredential.credential_id == credential_id,
            PasskeyCredential.user_id == student.id,
        )
    ).first()
    if credential is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "This passkey isn't registered to your account"
        )

    try:
        new_sign_count = passkeys.verify_assertion(
            request.app.state.settings, payload.credential, challenge, credential
        )
    except PasskeyVerificationError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passkey verification failed") from None

    now = utcnow()
    credential.sign_count = new_sign_count
    credential.last_used_at = now
    record = AttendanceRecord(
        session_id=live.id,
        student_id=student.id,
        status=AttendanceStatus.PRESENT,
        checked_in_at=now,
        passkey_credential_id=credential.id,
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already checked in") from None
    return CheckInResult(session_id=live.id, status="present", checked_in_at=now)
