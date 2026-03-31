"""Auth blueprint: request hooks, CSRF protection, login guard."""

import secrets
from functools import wraps

from flask import Blueprint, abort, g, redirect, request, session, url_for

bp = Blueprint("auth", __name__)


def generate_csrf_token() -> str:
    token = session.get("csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped_view


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
