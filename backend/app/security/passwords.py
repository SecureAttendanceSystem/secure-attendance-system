from werkzeug.security import check_password_hash, generate_password_hash

# A dummy hash used to keep login timing the same
# whether or not the email exists, so responses don't leak which emails are registered.
_DUMMY_HASH = generate_password_hash(generate_password_hash.__module__)


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        matched = check_password_hash(password_hash or _DUMMY_HASH, password)
        return bool(password_hash) and matched
    except ValueError:
        # Raised for a hash in a scheme generate_password_hash never produced
        # (e.g. a bcrypt hash seeded by some other tool). Treat as no match
        # rather than letting it surface as an unhandled 500.
        return False
