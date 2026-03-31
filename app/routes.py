"""All application HTTP routes in one place.

Each handler is deliberately thin: read request data → call tracker logic →
flash / redirect / render.  No SQL and no business logic lives here.
"""

import secrets
import sqlite3
from datetime import date

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.auth import bp as auth_bp
from app.auth import login_required
from app.auth.service import (
    DuplicateEmailError,
    authenticate_user,
    change_password,
    register_user,
)
from app.auth.validators import validate_email, validate_password
from app.tracker.dashboard.queries import get_dashboard_stats
from app.tracker.exercises.queries import (
    create_exercise,
    delete_exercise,
    get_exercise,
    list_exercises,
    update_exercise,
)
from app.tracker.progress.queries import (
    get_chart_data,
    get_exercise_for_user,
    get_progress_summary,
    get_top_exercises_chart_data,
)
from app.tracker.sessions.forms import (
    parse_optional_int,
    parse_reps_list,
    parse_session_date,
)
from app.tracker.sessions.queries import (
    delete_session,
    get_exercises_for_user,
    get_session_detail,
    get_session_detail_for_edit,
    get_session_for_user,
    get_sessions_for_day,
    save_session,
    update_session,
)

bp = Blueprint("routes", __name__)


@auth_bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        name = request.form.get("name", "").strip()
        date_of_birth = request.form.get("date_of_birth", "").strip()
        sex = request.form.get("sex", "").strip()
        raw_weight = request.form.get("weight", "").strip()

        weight: float | None = None
        error = validate_email(email) or validate_password(password)

        if error is None and password != confirm_password:
            error = "Passwords do not match."

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


@auth_bp.route("/login", methods=("GET", "POST"))
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


@auth_bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/")
def index():
    if g.user is None:
        return redirect(url_for("auth.login"))
    return redirect(url_for("routes.dashboard"))


@bp.route("/dashboard")
@login_required
def dashboard():
    try:
        year = int(request.args["year"]) if "year" in request.args else None
        month = int(request.args["month"]) if "month" in request.args else None
    except (ValueError, KeyError):
        year, month = None, None
    stats = get_dashboard_stats(g.user["id"], year=year, month=month)
    return render_template("dashboard.html", **stats)


@bp.route("/exercises", methods=("GET", "POST"))
@login_required
def exercises():
    user_id = g.user["id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        raw_sets = request.form.get("default_sets", "").strip()
        raw_reps = request.form.get("default_reps", "").strip()

        if not name:
            flash("Exercise name is required.", "error")
        else:
            try:
                default_sets = parse_optional_int(raw_sets, "Default sets", minimum=1)
                default_reps = parse_optional_int(raw_reps, "Default reps", minimum=0)
                create_exercise(user_id, name, default_sets, default_reps)
                return redirect(url_for("routes.exercises"))
            except ValueError as exc:
                flash(str(exc), "error")
            except sqlite3.IntegrityError:
                flash("Exercise with this name already exists.", "error")

    items = list_exercises(user_id)
    return render_template("exercises.html", exercises=items)


@bp.route("/exercises/<int:exercise_id>/delete", methods=("POST",))
@login_required
def delete_exercise_view(exercise_id):
    delete_exercise(exercise_id, g.user["id"])
    return redirect(url_for("routes.exercises"))


@bp.route("/exercises/<int:exercise_id>/edit", methods=("GET", "POST"))
@login_required
def edit_exercise_view(exercise_id):
    user_id = g.user["id"]
    exercise = get_exercise(exercise_id, user_id)
    if exercise is None:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        raw_sets = request.form.get("default_sets", "").strip()
        raw_reps = request.form.get("default_reps", "").strip()

        if not name:
            flash("Exercise name is required.", "error")
        else:
            try:
                default_sets = parse_optional_int(raw_sets, "Default sets", minimum=1)
                default_reps = parse_optional_int(raw_reps, "Default reps", minimum=0)
                update_exercise(exercise_id, user_id, name, default_sets, default_reps)
                flash("Exercise updated.", "success")
                return redirect(url_for("routes.exercises"))
            except ValueError as exc:
                flash(str(exc), "error")
            except sqlite3.IntegrityError:
                flash("Exercise with this name already exists.", "error")

    return render_template("exercise_edit.html", exercise=exercise)


@bp.route("/sessions/new", methods=("GET", "POST"))
@login_required
def new_session():
    user_id = g.user["id"]
    today = request.args.get("date", date.today().isoformat())
    exercises_list = get_exercises_for_user(user_id)

    def _render():
        return render_template(
            "session_new.html", exercises=exercises_list, today=today
        )

    if request.method == "POST":
        try:
            session_date = parse_session_date(request.form.get("session_date", ""))
        except ValueError as exc:
            flash(str(exc), "error")
            return _render()

        exercise_ids = request.form.getlist("exercise_id[]")
        reps_raw = request.form.getlist("reps[]")
        allowed_ids = {row["id"] for row in exercises_list}
        rows = []

        if not exercise_ids:
            flash("Add at least one exercise row.", "error")
            return _render()

        for idx, raw_id in enumerate(exercise_ids):
            raw_id = raw_id.strip()
            raw_reps = reps_raw[idx] if idx < len(reps_raw) else ""

            if not raw_id and not raw_reps.strip():
                continue

            if not raw_id:
                flash("Each session row must include an exercise.", "error")
                return _render()

            try:
                exercise_id = int(raw_id)
            except ValueError:
                flash("Please choose a valid exercise.", "error")
                return _render()

            if exercise_id not in allowed_ids:
                flash("Please choose a valid exercise.", "error")
                return _render()

            try:
                reps_list = parse_reps_list(raw_reps)
            except ValueError as exc:
                flash(str(exc), "error")
                return _render()

            rows.append((exercise_id, idx, reps_list))

        if not rows:
            flash("Add at least one complete exercise row.", "error")
            return _render()

        try:
            save_session(user_id, session_date, rows)
        except Exception:
            flash(
                "An error occurred while saving the session. Please try again.", "error"
            )
            return _render()

        return redirect(url_for("routes.dashboard"))

    return _render()


@bp.route("/sessions/<int:session_id>")
@login_required
def session_detail(session_id):
    sess = get_session_for_user(session_id, g.user["id"])
    if sess is None:
        abort(404)
    rows = get_session_detail(session_id)
    # Group flat rows into a list of {name, sets: [reps, ...]} dicts
    exercises = []
    for row in rows:
        if not exercises or exercises[-1]["name"] != row["exercise_name"]:
            exercises.append({"name": row["exercise_name"], "sets": []})
        exercises[-1]["sets"].append(row["reps"])
    return render_template("session_detail.html", session=sess, exercises=exercises)


@bp.route("/training-day/<session_date>")
@login_required
def training_day(session_date):
    """Show all sessions for a given day.

    If there is exactly one session redirect straight to session_detail.
    If there are none, redirect to new_session with the date pre-filled.
    """
    sessions = get_sessions_for_day(g.user["id"], session_date)
    if len(sessions) == 0:
        return redirect(url_for("routes.new_session", date=session_date))
    if len(sessions) == 1:
        return redirect(url_for("routes.session_detail", session_id=sessions[0]["id"]))
    return render_template(
        "training_day.html", session_date=session_date, sessions=sessions
    )


@bp.route("/sessions/<int:session_id>/delete", methods=("POST",))
@login_required
def delete_session_view(session_id):
    sess = get_session_for_user(session_id, g.user["id"])
    if sess is None:
        abort(404)
    delete_session(session_id, g.user["id"])
    flash("Session deleted.", "success")
    return redirect(url_for("routes.dashboard"))


@bp.route("/sessions/<int:session_id>/edit", methods=("GET", "POST"))
@login_required
def edit_session_view(session_id):
    user_id = g.user["id"]
    sess = get_session_for_user(session_id, user_id)
    if sess is None:
        abort(404)

    exercises_list = get_exercises_for_user(user_id)
    existing = get_session_detail_for_edit(session_id)

    def _render():
        return render_template(
            "session_edit.html",
            session=sess,
            exercises=exercises_list,
            existing=existing,
        )

    if request.method == "POST":
        try:
            session_date = parse_session_date(request.form.get("session_date", ""))
        except ValueError as exc:
            flash(str(exc), "error")
            return _render()

        exercise_ids = request.form.getlist("exercise_id[]")
        reps_raw = request.form.getlist("reps[]")
        allowed_ids = {row["id"] for row in exercises_list}
        rows = []

        if not exercise_ids:
            flash("Add at least one exercise row.", "error")
            return _render()

        for idx, raw_id in enumerate(exercise_ids):
            raw_id = raw_id.strip()
            raw_reps = reps_raw[idx] if idx < len(reps_raw) else ""
            if not raw_id and not raw_reps.strip():
                continue
            if not raw_id:
                flash("Each row must include an exercise.", "error")
                return _render()
            try:
                exercise_id = int(raw_id)
            except ValueError:
                flash("Please choose a valid exercise.", "error")
                return _render()
            if exercise_id not in allowed_ids:
                flash("Please choose a valid exercise.", "error")
                return _render()
            try:
                reps_list = parse_reps_list(raw_reps)
            except ValueError as exc:
                flash(str(exc), "error")
                return _render()
            rows.append((exercise_id, idx, reps_list))

        if not rows:
            flash("Add at least one complete exercise row.", "error")
            return _render()

        try:
            update_session(session_id, user_id, session_date, rows)
        except Exception:
            flash("An error occurred while saving. Please try again.", "error")
            return _render()

        flash("Session updated.", "success")
        return redirect(url_for("routes.session_detail", session_id=session_id))

    return _render()


@bp.route("/progress")
@login_required
def progress():
    exercises_list = get_progress_summary(g.user["id"])
    return render_template("progress.html", exercises=exercises_list)


@bp.route("/progress/<int:exercise_id>")
@login_required
def progress_detail(exercise_id):
    exercise = get_exercise_for_user(exercise_id, g.user["id"])
    if exercise is None:
        abort(404)
    return render_template("progress_detail.html", exercise=exercise)


@bp.route("/api/progress/<int:exercise_id>")
@login_required
def progress_data(exercise_id):
    exercise = get_exercise_for_user(exercise_id, g.user["id"])
    if exercise is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(get_chart_data(exercise_id, g.user["id"]))


@bp.route("/api/progress/overview")
@login_required
def progress_overview():
    return jsonify(get_top_exercises_chart_data(g.user["id"]))


@bp.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=g.user, pw_open=False)


@bp.route("/profile/edit", methods=("GET", "POST"))
@login_required
def edit_profile():
    from app.db import get_db

    user_id = g.user["id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        date_of_birth = request.form.get("date_of_birth", "").strip()
        raw_weight = request.form.get("weight", "").strip()

        if not name:
            flash("Name is required.", "error")
            return render_template("profile.html", user=g.user, pw_open=False)

        weight = None
        if raw_weight:
            try:
                weight = float(raw_weight.replace(",", "."))
                if weight <= 0:
                    raise ValueError
            except ValueError:
                flash("Weight must be a positive number.", "error")
                return render_template("profile.html", user=g.user, pw_open=False)

        db = get_db()
        db.execute(
            "UPDATE users SET name = ?, date_of_birth = ?, weight = ? WHERE id = ?",
            (name, date_of_birth or None, weight, user_id),
        )
        db.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("routes.profile"))

    return redirect(url_for("routes.profile"))


@bp.route("/profile/change-password", methods=("POST",))
@login_required
def change_password_view():
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    error = None
    if not current or not new or not confirm:
        error = "All password fields are required."
    elif pw_error := validate_password(new):
        error = pw_error
    elif new != confirm:
        error = "New passwords do not match."
    elif not change_password(g.user["id"], current, new):
        error = "Current password is incorrect."

    if error:
        flash(error, "error")
        return render_template("profile.html", user=g.user, pw_open=True)

    flash("Password changed successfully.", "success")
    return redirect(url_for("routes.profile"))
