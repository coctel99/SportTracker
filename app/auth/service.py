"""Auth business logic: registering and authenticating users."""

import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db


class DuplicateEmailError(Exception):
    """Raised when trying to register an e-mail that already exists."""


def register_user(email: str, password: str) -> None:
    """Insert a new user row.

    Raises:
        DuplicateEmailError: if the e-mail is already taken.
    """
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise DuplicateEmailError(email)


def authenticate_user(email: str, password: str):
    """Return the user row if credentials are valid, else None."""
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return None
    return user
