"""Auth blueprint: request hooks, CSRF protection, login guard."""

import re
import secrets
from functools import wraps

from flask import Blueprint, abort, g, redirect, request, session, url_for

bp = Blueprint("auth", __name__)

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


# ── CSRF helpers ──────────────────────────────────────────────────────────────


def generate_csrf_token() -> str:
    token = session.get("csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


# ── Login guard decorator ─────────────────────────────────────────────────────


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped_view


# ── Before-request hooks ──────────────────────────────────────────────────────


@bp.before_app_request
def load_logged_in_user():
    from app.db import get_db  # local import to avoid circular deps at module load

    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        return
    g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@bp.before_app_request
def validate_csrf_token():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        session_token = session.get("csrf_token")
        form_token = request.form.get("csrf_token")
        if session_token is None or form_token is None:
            abort(400)
        if not secrets.compare_digest(session_token, form_token):
            abort(400)


@bp.app_context_processor
def inject_csrf_token():
    return {"csrf_token": generate_csrf_token()}


# ── Routes ────────────────────────────────────────────────────────────────────

# Imported here so the blueprint picks them up when it is registered.
from app.auth import routes  # noqa: E402, F401
