
"""add student face embeddings

Revision ID: b92eafd93846
Revises: 0243a980bd89
Create Date: 2026-10-23 16:08:25.559598
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR


revision: str = "b92eafd93846"
down_revision: Union[str, Sequence[str], None] = "0243a980bd89"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector for facial embeddings
    op.execute("CREATE SCHEMA IF NOT EXISTS extensions")
    op.execute(
        "CREATE EXTENSION IF NOT EXISTS vector "
        "WITH SCHEMA extensions"
    )
    op.execute("SET LOCAL search_path TO public, extensions")

    # Create student face embeddings table
    op.create_table(
        "student_face_embeddings",
        sa.Column(
            "student_id",
            sa.Uuid(),
            sa.ForeignKey(
                "public.users.id",
                ondelete="CASCADE"
            ),
            primary_key=True,
        ),
        sa.Column(
            "embedding",
            VECTOR(512),
            nullable=False,
        ),
        sa.Column(
            "model_name",
            sa.Text(),
            nullable=False,
            server_default="Facenet512",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        schema="public",
    )

    # Restrict access through Supabase APIs
    op.execute(
        "ALTER TABLE public.student_face_embeddings "
        "ENABLE ROW LEVEL SECURITY"
    )


def downgrade() -> None:
    op.drop_table(
        "student_face_embeddings",
        schema="public",
    )
