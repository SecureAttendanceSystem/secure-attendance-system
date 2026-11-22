"""WebAuthn (passkey) ceremonies, wrapping py_webauthn.

Registration stores only the credential's public key. Check-in verifies a
signature over a fresh server challenge with that key; the biometric or PIN
check that unlocks the private key happens entirely on the student's device.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    AuthenticatorTransport,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.core.config import Settings
from app.models.enums import ChallengePurpose
from app.models.passkey import PasskeyCredential, WebAuthnChallenge
from app.models.user import User

CHALLENGE_TTL = timedelta(minutes=5)
CEREMONY_TIMEOUT_MS = 120_000
_KNOWN_TRANSPORTS = {transport.value for transport in AuthenticatorTransport}
# Malformed browser JSON can surface as a plain ValueError/KeyError/TypeError from parsing.
VERIFICATION_ERRORS = (WebAuthnException, ValueError, KeyError, TypeError)


class PasskeyVerificationError(Exception):
    """The browser's response did not verify against the issued challenge."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _descriptor(credential: PasskeyCredential) -> PublicKeyCredentialDescriptor:
    transports = [
        AuthenticatorTransport(value)
        for value in credential.transports or []
        if value in _KNOWN_TRANSPORTS
    ]
    return PublicKeyCredentialDescriptor(id=credential.credential_id, transports=transports or None)


def current_credentials(db: Session, user: User, settings: Settings) -> list[PasskeyCredential]:
    """The user's passkeys for this site. Passkeys made for another RP ID (or before
    rp_id was recorded) can't sign for this site, so they are ignored."""
    return list(
        db.scalars(
            select(PasskeyCredential).where(
                PasskeyCredential.user_id == user.id,
                PasskeyCredential.rp_id == settings.webauthn_rp_id,
            )
        ).all()
    )


def issue_challenge(
    db: Session,
    user: User,
    purpose: ChallengePurpose,
    challenge: bytes,
    class_session_id: UUID | None = None,
) -> WebAuthnChallenge:
    """Store a challenge, replacing any earlier one the user had for the same purpose."""
    db.execute(
        delete(WebAuthnChallenge).where(
            WebAuthnChallenge.user_id == user.id, WebAuthnChallenge.purpose == purpose
        )
    )
    row = WebAuthnChallenge(
        id=uuid4(),
        user_id=user.id,
        purpose=purpose,
        challenge=challenge,
        class_session_id=class_session_id,
        expires_at=utcnow() + CHALLENGE_TTL,
    )
    db.add(row)
    db.commit()
    return row


def consume_challenge(
    db: Session,
    challenge_id: UUID,
    user: User,
    purpose: ChallengePurpose,
    class_session_id: UUID | None = None,
) -> bytes:
    """Return the stored challenge and delete it, so each one is usable exactly once.

    The deletion is committed before the response is verified, so a failed
    attempt still burns the challenge.
    """
    row = db.get(WebAuthnChallenge, challenge_id)
    valid = (
        row is not None
        and row.user_id == user.id
        and row.purpose == purpose
        and row.class_session_id == class_session_id
    )
    if row is not None and row.user_id == user.id:
        db.delete(row)
        db.commit()
    if not valid or row.expires_at <= utcnow():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This passkey request expired or is invalid. Please try again.",
        )
    return row.challenge


def registration_options(settings: Settings, user: User) -> tuple[dict[str, Any], bytes]:
    options = generate_registration_options(
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.webauthn_rp_name,
        user_id=user.id.bytes,
        user_name=user.email,
        user_display_name=user.full_name,
        timeout=CEREMONY_TIMEOUT_MS,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )
    return json.loads(options_to_json(options)), options.challenge


def verify_registration(settings: Settings, credential: dict[str, Any], challenge: bytes):
    try:
        return verify_registration_response(
            credential=credential,
            expected_challenge=challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origins,
            require_user_verification=True,
        )
    except VERIFICATION_ERRORS as error:
        raise PasskeyVerificationError(str(error)) from error


def authentication_options(
    settings: Settings, credentials: list[PasskeyCredential]
) -> tuple[dict[str, Any], bytes]:
    options = generate_authentication_options(
        rp_id=settings.webauthn_rp_id,
        timeout=CEREMONY_TIMEOUT_MS,
        allow_credentials=[_descriptor(credential) for credential in credentials],
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    return json.loads(options_to_json(options)), options.challenge


def credential_id_of(response: dict[str, Any]) -> bytes:
    """Raw credential ID from a browser PublicKeyCredential JSON (base64url `rawId`)."""
    raw_id = response.get("rawId") or response.get("id")
    if not isinstance(raw_id, str):
        raise PasskeyVerificationError("Missing credential ID")
    try:
        return base64url_to_bytes(raw_id)
    except ValueError as error:
        raise PasskeyVerificationError("Malformed credential ID") from error


def verify_assertion(
    settings: Settings,
    response: dict[str, Any],
    challenge: bytes,
    credential: PasskeyCredential,
) -> int:
    """Verify a check-in assertion and return the authenticator's new sign count."""
    try:
        verified = verify_authentication_response(
            credential=response,
            expected_challenge=challenge,
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origins,
            credential_public_key=credential.public_key,
            credential_current_sign_count=credential.sign_count,
            require_user_verification=True,
        )
    except VERIFICATION_ERRORS as error:
        raise PasskeyVerificationError(str(error)) from error
    return verified.new_sign_count
