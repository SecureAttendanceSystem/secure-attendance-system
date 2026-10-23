from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.face_verification import router as face_verification

router = APIRouter()
router.include_router(health_router)
router.include_router(face_verification)
