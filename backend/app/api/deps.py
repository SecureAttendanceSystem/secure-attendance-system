from collections.abc import Generator
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.database.connection import get_database_engine
from app.models.user import User, UserRole
from app.security.tokens import decode_access_token

# Not OAuth2PasswordBearer: /auth/login takes a JSON body, not the OAuth2
# password-grant form, so that scheme's Swagger "Authorize" dialog wouldn't
# work against it. HTTPBearer instead just expects a token pasted in.
# auto_error=False lets get_current_user return a uniform 401 for both a
# missing and an invalid token, instead of FastAPI's default 403 on missing.
bearer_scheme = HTTPBearer(auto_error=False)


def get_db_session(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> Generator[Session]:
    with Session(engine) as session:
        yield session


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_db_session)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_error

    settings = request.app.state.settings
    try:
        payload = decode_access_token(credentials.credentials, settings)
        user_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credentials_error from None

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_role(*roles: UserRole):
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return dependency


require_admin = require_role(UserRole.ADMIN)
