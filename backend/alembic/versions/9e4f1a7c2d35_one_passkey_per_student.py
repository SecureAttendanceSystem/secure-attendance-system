"""one passkey per student per site

Revision ID: 9e4f1a7c2d35
Revises: 7c3d9e2a4b10
Create Date: 2026-11-22 23:00:00.000000

Records which site (WebAuthn RP ID) each passkey belongs to and allows one
passkey per student per site. Existing passkeys keep rp_id NULL: they don't
count toward the limit and are no longer offered at check-in, so students
set up one new passkey.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9e4f1a7c2d35'
down_revision: Union[str, Sequence[str], None] = '7c3d9e2a4b10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('passkey_credentials', sa.Column('rp_id', sa.String(length=253), nullable=True))
    op.drop_index('ix_passkey_credentials_user_id', table_name='passkey_credentials')
    op.create_index('uq_passkey_credentials_user_id_rp_id', 'passkey_credentials', ['user_id', 'rp_id'], unique=True)


def downgrade() -> None:
    op.drop_index('uq_passkey_credentials_user_id_rp_id', table_name='passkey_credentials')
    op.create_index('ix_passkey_credentials_user_id', 'passkey_credentials', ['user_id'], unique=False)
    op.drop_column('passkey_credentials', 'rp_id')
