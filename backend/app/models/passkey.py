"""WebAuthn passkeys.

The biometric (face, fingerprint) or PIN check happens on the student's own
device; the server only ever stores the credential's public key and verifies
signatures made with the matching private key, which never leaves the device.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import ChallengePurpose, enum_column


class PasskeyCredential(Base):
    __tablename__ = "passkey_credentials"
    __table_args__ = (
        # One passkey per student for each site (relying party). In production the
        # site never changes, so this is one passkey per student; a demo on a new
        # tunnel address gets a fresh slot. Rows from before rp_id was recorded have
        # NULL, which Postgres treats as distinct, so they never block a new one.
        Index("uq_passkey_credentials_user_id_rp_id", "user_id", "rp_id", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    # The WebAuthn RP ID (site) the passkey was created for; it only works there.
    rp_id: Mapped[str | None] = mapped_column(String(253))
    # Raw credential ID chosen by the authenticator (base64url on the wire).
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    # COSE-encoded public key from the registration response.
    public_key: Mapped[bytes] = mapped_column(LargeBinary)
    sign_count: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    transports: Mapped[list[str] | None] = mapped_column(ARRAY(String(32)))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WebAuthnChallenge(Base):
    """A single-use, short-lived challenge issued with registration or check-in options."""

    __tablename__ = "webauthn_challenges"
    __table_args__ = (Index("ix_webauthn_challenges_user_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    purpose: Mapped[ChallengePurpose] = mapped_column(
        enum_column(ChallengePurpose, "challenge_purpose")
    )
    challenge: Mapped[bytes] = mapped_column(LargeBinary)
    # Set for check-in challenges, so an assertion can't be replayed against another session.
    class_session_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("class_sessions.id", ondelete="CASCADE")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
