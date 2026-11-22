"""create courses, course instructors and enrollments

Revision ID: 1a0247c21066
Revises: b92eafd93846
Create Date: 2026-11-18 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1a0247c21066'
down_revision: Union[str, Sequence[str], None] = 'b92eafd93846'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('courses',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('term', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_courses')),
    sa.UniqueConstraint('code', 'term', name='uq_courses_code_term')
    )
    op.create_table('course_instructors',
    sa.Column('course_id', sa.Uuid(), nullable=False),
    sa.Column('professor_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_course_instructors_course_id_courses'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['professor_id'], ['users.id'], name=op.f('fk_course_instructors_professor_id_users')),
    sa.PrimaryKeyConstraint('course_id', 'professor_id', name=op.f('pk_course_instructors'))
    )
    op.create_table('enrollments',
    sa.Column('course_id', sa.Uuid(), nullable=False),
    sa.Column('student_id', sa.Uuid(), nullable=False),
    sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_enrollments_course_id_courses'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], name=op.f('fk_enrollments_student_id_users')),
    sa.PrimaryKeyConstraint('course_id', 'student_id', name=op.f('pk_enrollments'))
    )
    # Access goes through the FastAPI backend only; keep these tables closed
    # to Supabase's public Data API, matching the users table.
    op.execute('ALTER TABLE public.courses ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE public.course_instructors ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE public.enrollments ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_table('enrollments')
    op.drop_table('course_instructors')
    op.drop_table('courses')
