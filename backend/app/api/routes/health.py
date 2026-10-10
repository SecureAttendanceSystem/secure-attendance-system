import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import get_database_engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Check API liveness without requiring database access."""
    return HealthResponse()


@router.get("/health/db", response_model=HealthResponse)
def database_health(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> HealthResponse:
    """Check database connectivity without modifying application data."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("Database health check failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return HealthResponse()
