"""Passkey (WebAuthn) registration for students.

Only the credential's public key is stored; the biometric or PIN that
unlocks the private key never leaves the student's device.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db_session, require_role
from app.models.enums import ChallengePurpose
from app.models.passkey import PasskeyCredential
from app.models.user import User, UserRole
from app.schemas.live_session import CeremonyOptions, CeremonyResponse, PasskeyPublic
from app.services import passkeys
from app.services.passkeys import PasskeyVerificationError

router = APIRouter(prefix="/passkeys", tags=["Passkeys"])

DbSession = Annotated[Session, Depends(get_db_session)]
Student = Annotated[User, Depends(require_role(UserRole.STUDENT))]


def list_credentials(db: Session, user: User) -> list[PasskeyCredential]:
    return list(
        db.scalars(
            select(PasskeyCredential)
            .where(PasskeyCredential.user_id == user.id)
            .order_by(PasskeyCredential.created_at)
        ).all()
    )


@router.get("", response_model=list[PasskeyPublic])
def list_my_passkeys(db: DbSession, student: Student) -> list[PasskeyPublic]:
    return [PasskeyPublic.model_validate(credential) for credential in list_credentials(db, student)]


@router.post("/register/options", response_model=CeremonyOptions)
def registration_options(request: Request, db: DbSession, student: Student) -> CeremonyOptions:
    options, challenge = passkeys.registration_options(
        request.app.state.settings, student, list_credentials(db, student)
    )
    row = passkeys.issue_challenge(db, student, ChallengePurpose.PASSKEY_REGISTRATION, challenge)
    return CeremonyOptions(challenge_id=row.id, options=options)


@router.post("/register", response_model=PasskeyPublic, status_code=status.HTTP_201_CREATED)
def register_passkey(
    payload: CeremonyResponse, request: Request, db: DbSession, student: Student
) -> PasskeyPublic:
    challenge = passkeys.consume_challenge(
        db, payload.challenge_id, student, ChallengePurpose.PASSKEY_REGISTRATION
    )
    try:
        verified = passkeys.verify_registration(
            request.app.state.settings, payload.credential, challenge
        )
    except PasskeyVerificationError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Passkey registration failed") from None

    transports = payload.credential.get("response", {}).get("transports")
    credential = PasskeyCredential(
        user_id=student.id,
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        transports=[str(t) for t in transports] if isinstance(transports, list) else None,
        created_at=passkeys.utcnow(),
    )
    db.add(credential)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This passkey is already registered") from None
    db.refresh(credential)
    return PasskeyPublic.model_validate(credential)
