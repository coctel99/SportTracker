"""Input validation helpers for auth: email and password."""

import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MIN_PASSWORD_LEN = 8


def validate_email(email: str) -> str | None:
    """Return an error string if *email* is invalid, else None."""
    if not email:
        return "Email is required."
    if not _EMAIL_RE.match(email):
        return "Enter a valid email address."
    return None


def validate_password(password: str) -> str | None:
    """Return an error string if *password* is too weak, else None."""
    if not password:
        return "Password is required."
    if len(password) < MIN_PASSWORD_LEN:
        return f"Password must be at least {MIN_PASSWORD_LEN} characters."
    return None
