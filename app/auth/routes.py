"""Auth HTTP handlers: register, login, logout."""

import secrets

from flask import flash, redirect, render_template, request, session, url_for

from app.auth import bp, validate_email, validate_password
from app.auth.service import DuplicateEmailError, authenticate_user, register_user


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        error = validate_email(email) or validate_password(password)

        if error is None:
            try:
                register_user(email, password)
                return redirect(url_for("auth.login"))
            except DuplicateEmailError:
                error = "User already exists."

        flash(error)

    return render_template("register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = authenticate_user(email, password)
        if user is None:
            flash("Invalid credentials.")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("routes.dashboard"))

    return render_template("login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
