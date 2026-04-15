"""Input validation helpers for auth: email, password, username."""

import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")

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


def validate_username(username: str) -> str | None:
    """Return an error string if *username* is invalid, else None.

    Rules: 3–30 characters, only letters, digits, underscores, hyphens and dots.
    No spaces allowed.
    """
    if not username:
        return "Username is required."
    if len(username) < 3:
        return "Username must be at least 3 characters."
    if len(username) > 30:
        return "Username must be at most 30 characters."
    if not _USERNAME_RE.match(username):
        return "Username may only contain letters, digits, _, - and . (no spaces)."
    return None
