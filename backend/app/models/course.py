from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func

from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("code", "term", name="uq_courses_code_term"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(32))  # e.g. "ENGG 4000"
    title: Mapped[str] = mapped_column(String(200))
    term: Mapped[str] = mapped_column(String(16))  # e.g. "2026FALL"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CourseInstructor(Base):
    __tablename__ = "course_instructors"

    course_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    professor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), primary_key=True
    )


class Enrollment(Base):
    __tablename__ = "enrollments"

    course_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    student_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), primary_key=True
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
