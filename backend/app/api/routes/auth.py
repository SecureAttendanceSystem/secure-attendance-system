from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session, require_admin
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserPublic
from app.security.passwords import hash_password, verify_password
from app.security.tokens import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    credentials: LoginRequest,
    session: Annotated[Session, Depends(get_db_session)],
) -> TokenResponse:
    user = session.scalar(select(User).where(User.email == credentials.email.lower()))

    # verify_password still runs against a dummy hash when user is None, so a
    # nonexistent email doesn't return faster than a wrong password would.
    if not verify_password(credentials.password, user.password_hash if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")

    settings = request.app.state.settings
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


@router.get("/me", response_model=UserPublic)
def read_current_user(user: Annotated[User, Depends(get_current_user)]) -> UserPublic:
    return UserPublic.model_validate(user)


@router.post("/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    session: Annotated[Session, Depends(get_db_session)],
    _admin: Annotated[User, Depends(require_admin)],
) -> UserPublic:
    # Self-service signup is intentionally not exposed yet; only an
    # authenticated admin can provision accounts until that's revisited.
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    session.refresh(user)
    return UserPublic.model_validate(user)
