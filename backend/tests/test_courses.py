from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db_session
from app.models.course import Course, CourseInstructor, Enrollment
from app.models.user import User, UserRole
from app.security.tokens import create_access_token


class FakeScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeSession:
    """Stands in for a SQLAlchemy Session so routes can be tested without a database.

    `objects` maps (Model, primary key) to the row session.get() should return;
    composite keys are tuples, e.g. (CourseInstructor, (course_id, professor_id)).
    """

    def __init__(self, user, objects=None, listed=None):
        self.user = user
        self.objects = dict(objects or {})
        self.listed = listed or []
        self.statements = []
        self.added = []
        self.deleted = []
        self.committed = False
        self.rolled_back = False
        self.commit_error = None

    def get(self, model, pk):
        if model is User and pk == self.user.id:
            return self.user
        return self.objects.get((model, pk))

    def scalars(self, statement):
        self.statements.append(statement)
        return FakeScalarResult(self.listed)

    def add(self, obj):
        # Mimic the primary-key default SQLAlchemy would assign on flush.
        if isinstance(obj, Course) and obj.id is None:
            obj.id = uuid4()
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

    def commit(self):
        if self.commit_error is not None:
            raise self.commit_error
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def refresh(self, _obj):
        return None


def make_user(role=UserRole.STUDENT, **overrides):
    defaults = dict(
        id=uuid4(),
        email=f"{role.value}-{uuid4().hex[:6]}@unb.ca",
        full_name="Test User",
        password_hash="not-used-in-these-tests",
        role=role,
        is_active=True,
    )
    defaults.update(overrides)
    return User(**defaults)


def make_course(**overrides):
    defaults = dict(id=uuid4(), code="ENGG 4000", title="Capstone Design", term="2026FALL")
    defaults.update(overrides)
    return Course(**defaults)


def use_session(app, session):
    app.dependency_overrides[get_db_session] = lambda: session
    return session


def auth_header(settings, user):
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    return {"Authorization": f"Bearer {token}"}


# -- POST /courses ------------------------------------------------------------


def test_admin_can_create_a_course(app, client, settings):
    admin = make_user(UserRole.ADMIN)
    session = use_session(app, FakeSession(admin))

    response = client.post(
        "/courses",
        json={"code": "  ENGG 4000 ", "title": "Capstone Design", "term": "2026FALL"},
        headers=auth_header(settings, admin),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "ENGG 4000"
    assert body["title"] == "Capstone Design"
    assert body["term"] == "2026FALL"
    assert body["id"]
    assert session.committed is True


def test_professor_cannot_create_a_course(app, client, settings):
    professor = make_user(UserRole.PROFESSOR)
    session = use_session(app, FakeSession(professor))

    response = client.post(
        "/courses",
        json={"code": "ENGG 4000", "title": "Capstone Design", "term": "2026FALL"},
        headers=auth_header(settings, professor),
    )

    assert response.status_code == 403
    assert session.added == []


def test_create_course_rejects_a_duplicate_code_and_term(app, client, settings):
    admin = make_user(UserRole.ADMIN)
    session = use_session(app, FakeSession(admin))
    session.commit_error = IntegrityError("INSERT", {}, Exception("duplicate key"))

    response = client.post(
        "/courses",
        json={"code": "ENGG 4000", "title": "Capstone Design", "term": "2026FALL"},
        headers=auth_header(settings, admin),
    )

    assert response.status_code == 409
    assert session.rolled_back is True


def test_create_course_rejects_a_blank_code(app, client, settings):
    admin = make_user(UserRole.ADMIN)
    use_session(app, FakeSession(admin))

    response = client.post(
        "/courses",
        json={"code": "   ", "title": "Capstone Design", "term": "2026FALL"},
        headers=auth_header(settings, admin),
    )

    assert response.status_code == 422


# -- GET /courses ---------------------------------------------------------------


def test_listing_courses_requires_a_token(client):
    assert client.get("/courses").status_code == 401


def test_admin_lists_every_course(app, client, settings):
    admin = make_user(UserRole.ADMIN)
    course = make_course()
    session = use_session(app, FakeSession(admin, listed=[course]))

    response = client.get("/courses", headers=auth_header(settings, admin))

    assert response.status_code == 200
    assert [c["id"] for c in response.json()] == [str(course.id)]
    sql = str(session.statements[0])
    assert "course_instructors" not in sql
    assert "enrollments" not in sql


def test_professor_lists_only_courses_they_teach(app, client, settings):
    professor = make_user(UserRole.PROFESSOR)
    session = use_session(app, FakeSession(professor))

    response = client.get("/courses", headers=auth_header(settings, professor))

    assert response.status_code == 200
    statement = session.statements[0]
    assert "course_instructors" in str(statement)
    assert professor.id in statement.compile().params.values()


def test_student_lists_only_courses_they_are_enrolled_in(app, client, settings):
    student = make_user(UserRole.STUDENT)
    session = use_session(app, FakeSession(student))

    response = client.get("/courses", headers=auth_header(settings, student))

    assert response.status_code == 200
    statement = session.statements[0]
    assert "enrollments" in str(statement)
    assert student.id in statement.compile().params.values()


# -- GET /courses/{course_id} -----------------------------------------------------


def test_admin_can_read_any_course(app, client, settings):
    admin = make_user(UserRole.ADMIN)
    course = make_course()
    use_session(app, FakeSession(admin, objects={(Course, course.id): course}))

    response = client.get(f"/courses/{course.id}", headers=auth_header(settings, admin))

    assert response.status_code == 200
    assert response.json()["code"] == "ENGG 4000"


def test_professor_can_read_a_course_they_teach(app, client, settings):
    professor = make_user(UserRole.PROFESSOR)
    course = make_course()
    link = CourseInstructor(course_id=course.id, professor_id=professor.id)
    use_session(
        app,
        FakeSession(
            professor,
            objects={
                (Course, course.id): course,
                (CourseInstructor, (course.id, professor.id)): link,
            },
        ),
    )

    response = client.get(f"/courses/{course.id}", headers=auth_header(settings, professor))

    assert response.status_code == 200


def test_professor_gets_404_for_a_course_they_do_not_teach(app, client, settings):
    professor = make_user(UserRole.PROFESSOR)
    course = make_course()
    use_session(app, FakeSession(professor, objects={(Course, course.id): course}))

    response = client.get(f"/courses/{course.id}", headers=auth_header(settings, professor))

    assert response.status_code == 404


def test_student_can_read_a_course_they_are_enrolled_in(app, client, settings):
    student = make_user(UserRole.STUDENT)
    course = make_course()
    enrollment = Enrollment(course_id=course.id, student_id=student.id)
    use_session(
        app,
        FakeSession(
            student,
            objects={
                (Course, course.id): course,
                (Enrollment, (course.id, student.id)): enrollment,
            },
        ),
    )

    response = client.get(f"/courses/{course.id}", headers=auth_header(settings, student))

    assert response.status_code == 200


def test_student_gets_404_for_a_course_they_are_not_enrolled_in(app, client, settings):
    student = make_user(UserRole.STUDENT)
    course = make_course()
    use_session(app, FakeSession(student, objects={(Course, course.id): course}))

    response = client.get(f"/courses/{course.id}", headers=auth_header(settings, student))

    assert response.status_code == 404


def test_reading_a_missing_course_returns_404(app, client, settings):
    admin = make_user(UserRole.ADMIN)
    use_session(app, FakeSession(admin))

    response = client.get(f"/courses/{uuid4()}", headers=auth_header(settings, admin))

    assert response.status_code == 404


# -- PUT/DELETE /courses/{course_id}/instructors/{professor_id} ---------------------


def test_admin_can_assign_a_professor(app, client, settings):
    admin = make_user(UserRole.ADMIN)
    professor = make_user(UserRole.PROFESSOR)
    course = make_course()
    session = use_session(
        app,
        FakeSession(
            admin, objects={(Course, course.id): course, (User, professor.id): professor}
        ),
    )

    response = client.put(
        f"/courses/{course.id}/instructors/{professor.id}",
        headers=auth_header(settings, admin),
    )

    assert response.status_code == 204
    [link] = session.added
    assert (link.course_id, link.professor_id) == (course.id, professor.id)
    assert session.committed is True


def test_assigning_an_already_assigned_professor_is_a_no_op(app, client, settings):
    admin = make_user(UserRole.ADMIN)
    professor = make_user(UserRole.PROFESSOR)
    course = make_course()
    link = CourseInstructor(course_id=course.id, professor_id=professor.id)
    session = use_session(
        app,
        FakeSession(
            admin,
            objects={
                (Course, course.id): course,
                (User, professor.id): professor,
                (CourseInstructor, (course.id, professor.id)): link,
            },
        ),
    )

    response = client.put(
        f"/courses/{course.id}/instructors/{professor.id}",
        headers=auth_header(settings, admin),
    )

    assert response.status_code == 204
    assert session.added == []


def test_assigning_to_a_missing_course_returns_404(app, client, settings):
    admin = make_user(UserRole.ADMIN)
    professor = make_user(UserRole.PROFESSOR)
    use_session(app, FakeSession(admin, objects={(User, professor.id): professor}))

    response = client.put(
        f"/courses/{uuid4()}/instructors/{professor.id}",
        headers=auth_header(settings, admin),
    )

    assert response.status_code == 404


def test_a_student_cannot_be_assigned_as_instructor(app, client, settings):
    admin = make_user(UserRole.ADMIN)
    student = make_user(UserRole.STUDENT)
    course = make_course()
    session = use_session(
        app,
        FakeSession(admin, objects={(Course, course.id): course, (User, student.id): student}),
    )

    response = client.put(
        f"/courses/{course.id}/instructors/{student.id}",
        headers=auth_header(settings, admin),
    )

    assert response.status_code == 422
    assert session.added == []


def test_a_professor_cannot_assign_instructors(app, client, settings):
    professor = make_user(UserRole.PROFESSOR)
    course = make_course()
    session = use_session(app, FakeSession(professor, objects={(Course, course.id): course}))

    response = client.put(
        f"/courses/{course.id}/instructors/{professor.id}",
        headers=auth_header(settings, professor),
    )

    assert response.status_code == 403
    assert session.added == []


def test_admin_can_remove_an_assigned_professor(app, client, settings):
    admin = make_user(UserRole.ADMIN)
    course_id, professor_id = uuid4(), uuid4()
    link = CourseInstructor(course_id=course_id, professor_id=professor_id)
    session = use_session(
        app, FakeSession(admin, objects={(CourseInstructor, (course_id, professor_id)): link})
    )

    response = client.delete(
        f"/courses/{course_id}/instructors/{professor_id}",
        headers=auth_header(settings, admin),
    )

    assert response.status_code == 204
    assert session.deleted == [link]
    assert session.committed is True


def test_removing_a_professor_who_is_not_assigned_returns_404(app, client, settings):
    admin = make_user(UserRole.ADMIN)
    use_session(app, FakeSession(admin))

    response = client.delete(
        f"/courses/{uuid4()}/instructors/{uuid4()}",
        headers=auth_header(settings, admin),
    )

    assert response.status_code == 404
