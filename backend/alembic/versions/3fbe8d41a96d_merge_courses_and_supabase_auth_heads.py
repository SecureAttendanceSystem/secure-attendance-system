"""merge courses and supabase auth heads

Revision ID: 3fbe8d41a96d
Revises: 1a0247c21066, f1a2b3c4d5e6
Create Date: 2026-11-22 16:10:49.283894

The courses migration and the Supabase auth migration were written on
separate branches, both on top of b92eafd93846. They touch different tables,
so this revision only joins the two heads and makes no schema changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3fbe8d41a96d'
down_revision: Union[str, Sequence[str], None] = ('1a0247c21066', 'f1a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
