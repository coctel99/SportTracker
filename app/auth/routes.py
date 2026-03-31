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
        name = request.form.get("name", "").strip()
        date_of_birth = request.form.get("date_of_birth", "").strip()
        sex = request.form.get("sex", "").strip()
        raw_weight = request.form.get("weight", "").strip()

        weight: float | None = None
        error = validate_email(email) or validate_password(password)

        if error is None and not name:
            error = "Name is required."

        if error is None and sex not in ("male", "female"):
            error = "Please select your biological sex."

        if error is None and raw_weight:
            try:
                weight = float(raw_weight.replace(",", "."))
                if weight <= 0:
                    error = "Weight must be a positive number."
            except ValueError:
                error = "Weight must be a valid number."

        if error is None:
            try:
                register_user(
                    email,
                    password,
                    name=name,
                    date_of_birth=date_of_birth or None,
                    sex=sex,
                    weight=weight,
                )
                user = authenticate_user(email, password)
                session.clear()
                session["user_id"] = user["id"]
                session["csrf_token"] = secrets.token_urlsafe(32)
                return redirect(url_for("routes.dashboard"))
            except DuplicateEmailError:
                error = "User already exists."

        flash(error, "error")

    return render_template(
        "register.html",
        form_name=request.form.get("name", ""),
        form_email=request.form.get("email", ""),
        form_dob=request.form.get("date_of_birth", ""),
        form_sex=request.form.get("sex", ""),
        form_weight=request.form.get("weight", ""),
    )


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = authenticate_user(email, password)
        if user is None:
            flash("Invalid credentials.", "error")
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
