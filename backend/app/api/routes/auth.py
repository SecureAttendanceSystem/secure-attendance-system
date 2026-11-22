from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session, require_admin
from app.models.user import User
from app.schemas.auth import SignupRequest, UserPublic

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=UserPublic)
def read_current_user(user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    return UserPublic.model_validate(user)


@router.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def signup(
    request: Request,
    payload: SignupRequest,
    session: Annotated[Session, Depends(get_db_session)],
    _admin: Annotated[User, Depends(require_admin)],
) -> UserPublic:
    # Self-service signup is intentionally not exposed yet; only an
    # authenticated admin can provision accounts until that's revisited.
    # Credentials live in Supabase's auth.users, created here via its Admin
    # API; public.users only holds the profile (role, name) keyed by the
    # same id.
    settings = request.app.state.settings
    admin_users_url = f"{settings.supabase_url}/auth/v1/admin/users"
    service_key = settings.supabase_service_role_key.get_secret_value()
    headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}

    response = httpx.post(
        admin_users_url,
        headers=headers,
        json={
            "email": payload.email.lower(),
            "password": payload.password,
            "email_confirm": True,
        },
        timeout=10,
    )
    if response.status_code >= 400:
        body = response.json() if response.content else {}
        error_code = body.get("error_code") or body.get("code")
        message = body.get("msg") or body.get("message") or "Could not create the account."
        if error_code in {"email_exists", "user_already_exists"}:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, message)

    user_id = UUID(response.json()["id"])
    profile = User(
        id=user_id,
        email=payload.email.lower(),
        full_name=payload.full_name,
        role=payload.role,
    )
    session.add(profile)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # Don't leave an orphaned Supabase account with no matching profile.
        httpx.delete(f"{admin_users_url}/{user_id}", headers=headers, timeout=10)
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    session.refresh(profile)
    return UserPublic.model_validate(profile)
