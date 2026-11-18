from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session, require_admin
from app.models.course import Course, CourseInstructor, Enrollment
from app.models.user import User, UserRole
from app.schemas.course import CourseCreate, CoursePublic

router = APIRouter(prefix="/courses", tags=["Courses"])

DbSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]


def can_view_course(session: Session, user: User, course_id: UUID) -> bool:
    """Admins see every course, professors the ones they teach, students the ones they take."""
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.PROFESSOR:
        return session.get(CourseInstructor, (course_id, user.id)) is not None
    return session.get(Enrollment, (course_id, user.id)) is not None


@router.post("", response_model=CoursePublic, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, session: DbSession, _admin: AdminUser) -> CoursePublic:
    course = Course(code=payload.code, title=payload.title, term=payload.term)
    session.add(course)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A course with this code already exists for this term"
        ) from None
    session.refresh(course)
    return CoursePublic.model_validate(course)


@router.get("", response_model=list[CoursePublic])
def list_my_courses(session: DbSession, user: CurrentUser) -> list[CoursePublic]:
    statement = select(Course)
    if user.role == UserRole.PROFESSOR:
        statement = statement.join(
            CourseInstructor, CourseInstructor.course_id == Course.id
        ).where(CourseInstructor.professor_id == user.id)
    elif user.role == UserRole.STUDENT:
        statement = statement.join(Enrollment, Enrollment.course_id == Course.id).where(
            Enrollment.student_id == user.id
        )
    statement = statement.order_by(Course.term.desc(), Course.code)
    return [CoursePublic.model_validate(course) for course in session.scalars(statement).all()]


@router.get("/{course_id}", response_model=CoursePublic)
def read_course(course_id: UUID, session: DbSession, user: CurrentUser) -> CoursePublic:
    course = session.get(Course, course_id)
    # 404 rather than 403 for courses the caller can't see, so IDs can't be probed.
    if course is None or not can_view_course(session, user, course_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    return CoursePublic.model_validate(course)


@router.put("/{course_id}/instructors/{professor_id}", status_code=status.HTTP_204_NO_CONTENT)
def assign_instructor(
    course_id: UUID, professor_id: UUID, session: DbSession, _admin: AdminUser
) -> None:
    if session.get(Course, course_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")

    professor = session.get(User, professor_id)
    if professor is None or professor.role != UserRole.PROFESSOR or not professor.is_active:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "User is not an active professor"
        )

    # PUT is idempotent: assigning an existing instructor again is a no-op.
    if session.get(CourseInstructor, (course_id, professor_id)) is not None:
        return

    session.add(CourseInstructor(course_id=course_id, professor_id=professor_id))
    try:
        session.commit()
    except IntegrityError:
        # A concurrent request assigned the same professor or deleted the course.
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Could not assign professor") from None


@router.delete(
    "/{course_id}/instructors/{professor_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_instructor(
    course_id: UUID, professor_id: UUID, session: DbSession, _admin: AdminUser
) -> None:
    link = session.get(CourseInstructor, (course_id, professor_id))
    if link is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Professor is not assigned to this course"
        )
    session.delete(link)
    session.commit()
