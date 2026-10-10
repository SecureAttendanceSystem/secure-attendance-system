from fastapi import Request
from sqlalchemy import Engine, create_engine

from app.core.config import Settings


def create_database_engine(settings: Settings) -> Engine:
    # Engine creation is lazy: liveness and API docs work without a live database.
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


def get_database_engine(request: Request) -> Engine:
    return request.app.state.database_engine
