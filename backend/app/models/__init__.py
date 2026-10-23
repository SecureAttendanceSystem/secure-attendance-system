"""Import each model here so Alembic discovers its table metadata.

All models should inherit from app.database.base.Base.
"""

from app.models.course import Course, CourseInstructor, Enrollment
from app.models.room import Room
from app.models.user import User, UserRole

__all__ = [
    "Course",
    "CourseInstructor",
    "Enrollment",
    "Room",
    "User",
    "UserRole",
]
