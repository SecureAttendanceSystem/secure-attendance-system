"""Import each model here so Alembic discovers its table metadata.

All models should inherit from app.database.base.Base.
"""

from app.models.user import User, UserRole

__all__ = ["User", "UserRole"]
