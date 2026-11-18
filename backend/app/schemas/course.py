from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

# Lengths match the columns in app.models.course.Course.
CourseCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
CourseTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CourseTerm = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=16)]


class CourseCreate(BaseModel):
    code: CourseCode
    title: CourseTitle
    term: CourseTerm


class CoursePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    title: str
    term: str
