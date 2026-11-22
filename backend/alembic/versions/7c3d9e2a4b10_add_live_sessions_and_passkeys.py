"""add live sessions, attendance records and passkeys

Revision ID: 7c3d9e2a4b10
Revises: 3fbe8d41a96d
Create Date: 2026-11-22 17:00:00.000000

Creates the tables for a professor-run live attendance session and
passkey (WebAuthn) check-in. Rooms are created too because class_sessions
references them, but a live session doesn't need one. The face embedding
table is left as it is.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '7c3d9e2a4b10'
down_revision: Union[str, Sequence[str], None] = '3fbe8d41a96d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_TABLES = (
    'rooms',
    'class_sessions',
    'passkey_credentials',
    'attendance_records',
    'webauthn_challenges',
)


def upgrade() -> None:
    op.create_table('rooms',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('building', sa.String(length=100), nullable=False),
    sa.Column('room_number', sa.String(length=32), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('geofence_radius_m', sa.Integer(), server_default=sa.text('50'), nullable=False),
    sa.Column('ble_beacon_uuid', sa.String(length=64), nullable=True),
    sa.CheckConstraint('geofence_radius_m > 0', name=op.f('ck_rooms_geofence_positive')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rooms')),
    sa.UniqueConstraint('building', 'room_number', name='uq_rooms_building_room_number')
    )
    op.create_table('class_sessions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('course_id', sa.Uuid(), nullable=False),
    sa.Column('room_id', sa.Uuid(), nullable=True),
    sa.Column('started_by', sa.Uuid(), nullable=True),
    sa.Column('scheduled_start', sa.DateTime(timezone=True), nullable=True),
    sa.Column('scheduled_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('actual_start', sa.DateTime(timezone=True), nullable=True),
    sa.Column('actual_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.Enum('scheduled', 'active', 'ended', 'cancelled', name='session_status', native_enum=False, create_constraint=True), server_default='scheduled', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('scheduled_end > scheduled_start', name=op.f('ck_class_sessions_time_order')),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], name=op.f('fk_class_sessions_course_id_courses'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], name=op.f('fk_class_sessions_room_id_rooms')),
    sa.ForeignKeyConstraint(['started_by'], ['users.id'], name=op.f('fk_class_sessions_started_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_class_sessions'))
    )
    op.create_index('ix_class_sessions_course_id_scheduled_start', 'class_sessions', ['course_id', 'scheduled_start'], unique=False)
    op.create_index('uq_class_sessions_active_course', 'class_sessions', ['course_id'], unique=True, postgresql_where=sa.text("status = 'active'"))

    op.create_table('passkey_credentials',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('credential_id', sa.LargeBinary(), nullable=False),
    sa.Column('public_key', sa.LargeBinary(), nullable=False),
    sa.Column('sign_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('transports', postgresql.ARRAY(sa.String(length=32)), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_passkey_credentials_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_passkey_credentials')),
    sa.UniqueConstraint('credential_id', name=op.f('uq_passkey_credentials_credential_id'))
    )
    op.create_index('ix_passkey_credentials_user_id', 'passkey_credentials', ['user_id'], unique=False)

    op.create_table('attendance_records',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('student_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Enum('present', 'rejected', 'flagged', 'excused', 'absent', name='attendance_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('checked_in_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('passkey_credential_id', sa.Uuid(), nullable=True),
    sa.Column('reviewed_by', sa.Uuid(), nullable=True),
    sa.Column('review_note', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['class_sessions.id'], name=op.f('fk_attendance_records_session_id_class_sessions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['student_id'], ['users.id'], name=op.f('fk_attendance_records_student_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['passkey_credential_id'], ['passkey_credentials.id'], name=op.f('fk_attendance_records_passkey_credential_id_passkey_credentials'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], name=op.f('fk_attendance_records_reviewed_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attendance_records')),
    sa.UniqueConstraint('session_id', 'student_id', name='uq_attendance_records_session_student')
    )
    op.create_index('ix_attendance_records_student_id', 'attendance_records', ['student_id'], unique=False)

    op.create_table('webauthn_challenges',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('purpose', sa.Enum('passkey_registration', 'check_in', name='challenge_purpose', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('challenge', sa.LargeBinary(), nullable=False),
    sa.Column('class_session_id', sa.Uuid(), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_webauthn_challenges_user_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['class_session_id'], ['class_sessions.id'], name=op.f('fk_webauthn_challenges_class_session_id_class_sessions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_webauthn_challenges'))
    )
    op.create_index('ix_webauthn_challenges_user_id', 'webauthn_challenges', ['user_id'], unique=False)

    # Access goes through the FastAPI backend only; keep these tables closed
    # to Supabase's public Data API, matching the other tables.
    for table in NEW_TABLES:
        op.execute(f'ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
