"""create users

Revision ID: 0243a980bd89
Revises: 
Create Date: 2026-10-09 17:05:33.412701
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0243a980bd89'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('full_name', sa.String(length=200), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role', sa.Enum('student', 'professor', 'admin', name='user_role', native_enum=False, create_constraint=True), server_default='student', nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    # Custom JWT authentication is handled by FastAPI. Keep user records
    # inaccessible through Supabase's public Data API without explicit policies.
    op.execute('ALTER TABLE public.users ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_table('users')
