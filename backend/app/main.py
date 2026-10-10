import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.database.connection import create_database_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = app.state.settings
    configure_logging(settings.log_level)
    logger.info("Starting %s (%s)", settings.app_name, settings.environment)
    try:
        yield
    finally:
        app.state.database_engine.dispose()
        logger.info("Application shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.state.settings = settings
    application.state.database_engine = create_database_engine(settings)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    register_exception_handlers(application)
    application.include_router(router)
    return application


app = create_app()
