"""migrate users to supabase auth

Revision ID: f1a2b3c4d5e6
Revises: b92eafd93846
Create Date: 2026-11-05 15:55:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'b92eafd93846'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Credentials now live in Supabase's auth.users; this table is just a
    # profile (role, name) keyed by the same id, so password_hash is gone
    # and id must match an existing auth.users row. On a real Supabase
    # database auth.users already exists; CI and local dev run against a
    # plain Postgres container with no such schema, so create a minimal
    # stand-in there (guarded, so this never touches a real Supabase db).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'auth') THEN
                CREATE SCHEMA auth;
                CREATE TABLE auth.users (id uuid PRIMARY KEY);
            END IF;
        END $$;
        """
    )
    op.drop_column('users', 'password_hash')
    op.create_foreign_key(
        'fk_users_id_auth_users',
        'users', 'users',
        ['id'], ['id'],
        source_schema='public', referent_schema='auth',
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('fk_users_id_auth_users', 'users', schema='public', type_='foreignkey')
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))
