"""Auth business logic: registering and authenticating users."""

import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_db


class DuplicateEmailError(Exception):
    """Raised when trying to register an e-mail that already exists."""


class DuplicateUsernameError(Exception):
    """Raised when trying to register a username that already exists."""


def register_user(
    email: str,
    password: str,
    username: str,
    name: str | None = None,
    date_of_birth: str | None = None,
    sex: str | None = None,
    weight: float | None = None,
) -> None:
    """Insert a new user row.

    Raises:
        DuplicateEmailError: if the e-mail is already taken.
        DuplicateUsernameError: if the username is already taken.
    """
    db = get_db()
    # Check uniqueness separately for better error messages
    if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
        raise DuplicateEmailError(email)
    if db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        raise DuplicateUsernameError(username)
    try:
        db.execute(
            "INSERT INTO users (email, username, password_hash, name, date_of_birth, sex, weight) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                email,
                username,
                generate_password_hash(password),
                name or None,
                date_of_birth or None,
                sex or None,
                weight,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise DuplicateEmailError(email)


def authenticate_user(login: str, password: str):
    """Return the user row if credentials are valid, else None.

    *login* may be an email address or a username (case-insensitive).
    """
    db = get_db()
    login_lower = login.strip().lower()
    # Try email first, then username
    user = db.execute("SELECT * FROM users WHERE email = ?", (login_lower,)).fetchone()
    if user is None:
        user = db.execute(
            "SELECT * FROM users WHERE LOWER(username) = ?", (login_lower,)
        ).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return None
    return user


def change_password(user_id: int, current_password: str, new_password: str) -> bool:
    """Update the user's password.

    Returns True on success, False if current_password is wrong.
    """
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], current_password):
        return False
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_password), user_id),
    )
    db.commit()
    return True
