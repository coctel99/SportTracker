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
    make_response,
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
    DuplicateUsernameError,
    authenticate_user,
    change_password,
    register_user,
)
from app.auth.validators import validate_email, validate_password, validate_username
from app.tracker.dashboard.queries import get_dashboard_stats
from app.tracker.exercises.queries import (
    create_exercise,
    delete_exercise,
    get_exercise,
    list_exercises,
    update_exercise,
)
from app.tracker.export import export_csv, export_json
from app.tracker.progress.queries import (
    get_chart_data,
    get_exercise_for_user,
    get_progress_summary,
    get_top_exercises_chart_data,
)
from app.tracker.sessions.forms import (
    parse_optional_int,
    parse_session_date,
    parse_sets_data,
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
    if g.user is not None:
        return redirect(url_for("routes.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        name = request.form.get("name", "").strip()
        date_of_birth = request.form.get("date_of_birth", "").strip()
        sex = request.form.get("sex", "").strip()
        raw_weight = request.form.get("weight", "").strip()

        weight: float | None = None
        error = (
            validate_email(email)
            or validate_password(password)
            or validate_username(username)
        )

        if error is None and password != confirm_password:
            error = "Passwords do not match."

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
                    username=username,
                    name=name or None,
                    date_of_birth=date_of_birth or None,
                    sex=sex,
                    weight=weight,
                )
                user = authenticate_user(email, password)
                session.clear()
                session.permanent = True
                session["user_id"] = user["id"]
                session["csrf_token"] = secrets.token_urlsafe(32)
                return redirect(url_for("routes.dashboard"))
            except DuplicateEmailError:
                error = "An account with this email already exists."
            except DuplicateUsernameError:
                error = "This username is already taken."

        flash(error, "error")

    return render_template(
        "register.html",
        form_username=request.form.get("username", ""),
        form_name=request.form.get("name", ""),
        form_email=request.form.get("email", ""),
        form_dob=request.form.get("date_of_birth", ""),
        form_sex=request.form.get("sex", ""),
        form_weight=request.form.get("weight", ""),
    )


@auth_bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user is not None:
        return redirect(url_for("routes.dashboard"))

    if request.method == "POST":
        login_input = request.form.get("login", "").strip()
        password = request.form.get("password", "")

        user = authenticate_user(login_input, password)
        if user is None:
            flash("Invalid credentials.", "error")
        else:
            session.clear()
            session.permanent = True
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
        raw_dur = request.form.get("default_duration", "").strip()
        raw_dur_unit = request.form.get("default_duration_unit", "").strip()

        if not name:
            flash("Exercise name is required.", "error")
        else:
            try:
                from app.tracker.sessions.forms import parse_duration

                default_sets = parse_optional_int(raw_sets, "Default sets", minimum=1)
                default_reps = parse_optional_int(raw_reps, "Default reps", minimum=0)
                default_duration_seconds = None
                default_duration_unit = None
                if raw_dur:
                    if raw_dur_unit not in ("seconds", "minutes", "hours"):
                        raise ValueError(
                            "Please select a duration unit (seconds, minutes, or hours)."
                        )
                    default_duration_seconds = parse_duration(raw_dur, raw_dur_unit)
                    default_duration_unit = raw_dur_unit
                create_exercise(
                    user_id,
                    name,
                    default_sets,
                    default_reps,
                    default_duration_seconds,
                    default_duration_unit,
                )
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
        raw_dur = request.form.get("default_duration", "").strip()
        raw_dur_unit = request.form.get("default_duration_unit", "").strip()

        if not name:
            flash("Exercise name is required.", "error")
        else:
            try:
                from app.tracker.sessions.forms import parse_duration

                default_sets = parse_optional_int(raw_sets, "Default sets", minimum=1)
                default_reps = parse_optional_int(raw_reps, "Default reps", minimum=0)
                default_duration_seconds = None
                default_duration_unit = None
                if raw_dur:
                    if raw_dur_unit not in ("seconds", "minutes", "hours"):
                        raise ValueError(
                            "Please select a duration unit (seconds, minutes, or hours)."
                        )
                    default_duration_seconds = parse_duration(raw_dur, raw_dur_unit)
                    default_duration_unit = raw_dur_unit
                update_exercise(
                    exercise_id,
                    user_id,
                    name,
                    default_sets,
                    default_reps,
                    default_duration_seconds,
                    default_duration_unit,
                )
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
        duration_raw = request.form.getlist("duration[]")
        duration_unit_raw = request.form.getlist("duration_unit[]")
        allowed_ids = {row["id"] for row in exercises_list}
        rows = []

        if not exercise_ids:
            flash("Add at least one exercise row.", "error")
            return _render()

        for idx, raw_id in enumerate(exercise_ids):
            raw_id = raw_id.strip()
            raw_reps = reps_raw[idx] if idx < len(reps_raw) else ""
            raw_dur = duration_raw[idx] if idx < len(duration_raw) else ""
            raw_unit = (
                duration_unit_raw[idx] if idx < len(duration_unit_raw) else "seconds"
            )

            if not raw_id and not raw_reps.strip() and not raw_dur.strip():
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
                sets_data = parse_sets_data(raw_reps, raw_dur, raw_unit)
            except ValueError as exc:
                flash(str(exc), "error")
                return _render()

            rows.append((exercise_id, idx, sets_data))

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

        return redirect(url_for("routes.training_day", session_date=session_date))

    return _render()


@bp.route("/sessions/<int:session_id>")
@login_required
def session_detail(session_id):
    """Show the detail page for a single session."""
    sess = get_session_for_user(session_id, g.user["id"])
    if sess is None:
        abort(404)
    rows = get_session_detail(session_id)
    # Group rows by exercise name (preserving order)
    exercises = []
    seen = {}
    for row in rows:
        name = row["exercise_name"]
        if name not in seen:
            entry = {"name": name, "sets": []}
            seen[name] = entry
            exercises.append(entry)
        seen[name]["sets"].append((row["reps"], row["duration_seconds"]))
    return render_template("session_detail.html", session=sess, exercises=exercises)


@bp.route("/training-day/<session_date>")
@login_required
def training_day(session_date):
    """Show all sessions for a given day.

    If there are none, redirect to new_session with the date pre-filled.
    Otherwise always render the training_day page so the user can add more sessions.
    """
    sessions = get_sessions_for_day(g.user["id"], session_date)
    if len(sessions) == 0:
        return redirect(url_for("routes.new_session", date=session_date))
    return render_template(
        "training_day.html", session_date=session_date, sessions=sessions
    )


@bp.route("/sessions/<int:session_id>/delete", methods=("POST",))
@login_required
def delete_session_view(session_id):
    sess = get_session_for_user(session_id, g.user["id"])
    if sess is None:
        abort(404)
    session_date = sess["session_date"]
    delete_session(session_id, g.user["id"])
    flash("Session deleted.", "success")
    # If no sessions remain for that day, go to dashboard; otherwise stay on the day
    remaining = get_sessions_for_day(g.user["id"], session_date)
    if remaining:
        return redirect(url_for("routes.training_day", session_date=session_date))
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
        duration_raw = request.form.getlist("duration[]")
        duration_unit_raw = request.form.getlist("duration_unit[]")
        allowed_ids = {row["id"] for row in exercises_list}
        rows = []

        if not exercise_ids:
            flash("Add at least one exercise row.", "error")
            return _render()

        for idx, raw_id in enumerate(exercise_ids):
            raw_id = raw_id.strip()
            raw_reps = reps_raw[idx] if idx < len(reps_raw) else ""
            raw_dur = duration_raw[idx] if idx < len(duration_raw) else ""
            raw_unit = (
                duration_unit_raw[idx] if idx < len(duration_unit_raw) else "seconds"
            )
            if not raw_id and not raw_reps.strip() and not raw_dur.strip():
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
                sets_data = parse_sets_data(raw_reps, raw_dur, raw_unit)
            except ValueError as exc:
                flash(str(exc), "error")
                return _render()
            rows.append((exercise_id, idx, sets_data))

        if not rows:
            flash("Add at least one complete exercise row.", "error")
            return _render()

        try:
            update_session(session_id, user_id, session_date, rows)
        except Exception:
            flash("An error occurred while saving. Please try again.", "error")
            return _render()

        flash("Session updated.", "success")
        return redirect(url_for("routes.training_day", session_date=session_date))

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


@bp.route("/users")
@login_required
def users_list():
    from app.db import get_db

    q = request.args.get("q", "").strip()
    db = get_db()
    user_id = g.user["id"]

    if q:
        rows = db.execute(
            """
            SELECT u.id, u.username, u.name,
                   (SELECT COUNT(*) FROM friends f2 WHERE f2.user_id = u.id) AS friend_count,
                   EXISTS(SELECT 1 FROM friends f3
                          WHERE f3.user_id = ? AND f3.friend_id = u.id) AS is_friend
            FROM users u
            WHERE u.id != ?
              AND (LOWER(u.username) LIKE ? OR LOWER(u.name) LIKE ?)
            ORDER BY friend_count DESC, u.username ASC
            LIMIT 50
            """,
            (user_id, user_id, f"%{q.lower()}%", f"%{q.lower()}%"),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT u.id, u.username, u.name,
                   (SELECT COUNT(*) FROM friends f2 WHERE f2.user_id = u.id) AS friend_count,
                   EXISTS(SELECT 1 FROM friends f3
                          WHERE f3.user_id = ? AND f3.friend_id = u.id) AS is_friend
            FROM users u
            WHERE u.id != ?
            ORDER BY friend_count DESC, u.username ASC
            LIMIT 50
            """,
            (user_id, user_id),
        ).fetchall()

    return render_template("users.html", users=rows, q=q)


@bp.route("/users/<int:target_id>/add-friend", methods=("POST",))
@login_required
def add_friend(target_id):
    from app.db import get_db

    db = get_db()
    user_id = g.user["id"]
    if target_id == user_id:
        flash("You cannot add yourself as a friend.", "error")
        return redirect(url_for("routes.users_list"))

    target = db.execute("SELECT id FROM users WHERE id = ?", (target_id,)).fetchone()
    if target is None:
        abort(404)

    try:
        db.execute(
            "INSERT OR IGNORE INTO friends (user_id, friend_id) VALUES (?, ?)",
            (user_id, target_id),
        )
        db.commit()
    except Exception:
        pass

    # Redirect back to where we came from
    next_url = request.form.get("next") or url_for("routes.users_list")
    return redirect(next_url)


@bp.route("/users/<int:target_id>/remove-friend", methods=("POST",))
@login_required
def remove_friend(target_id):
    from app.db import get_db

    db = get_db()
    db.execute(
        "DELETE FROM friends WHERE user_id = ? AND friend_id = ?",
        (g.user["id"], target_id),
    )
    db.commit()

    next_url = request.form.get("next") or url_for("routes.users_list")
    return redirect(next_url)


@bp.route("/profile")
@login_required
def profile():
    data = _build_profile_data(g.user["id"])
    data["is_own_profile"] = True
    data["is_friend"] = False
    data["friend_count"] = _get_friend_count(g.user["id"])
    return render_template("profile.html", user=g.user, **data)


@bp.route("/users/<username>")
@login_required
def user_profile(username):
    from app.db import get_db

    db = get_db()
    target = db.execute(
        "SELECT * FROM users WHERE LOWER(username) = ?", (username.lower(),)
    ).fetchone()
    if target is None:
        abort(404)

    # Own profile → redirect to canonical /profile
    if target["id"] == g.user["id"]:
        return redirect(url_for("routes.profile"))

    is_friend = (
        db.execute(
            "SELECT 1 FROM friends WHERE user_id = ? AND friend_id = ?",
            (g.user["id"], target["id"]),
        ).fetchone()
        is not None
    )

    data = _build_profile_data(target["id"])
    data["is_own_profile"] = False
    data["is_friend"] = is_friend
    data["friend_count"] = _get_friend_count(target["id"])
    return render_template("profile.html", user=target, **data)


def _get_friend_count(user_id: int) -> int:
    from app.db import get_db

    return (
        get_db()
        .execute("SELECT COUNT(*) FROM friends WHERE user_id = ?", (user_id,))
        .fetchone()[0]
    )


def _build_profile_data(user_id: int) -> dict:
    """Return all stats needed to render profile.html for *user_id*."""
    from datetime import date, timedelta

    from app.db import get_db

    db = get_db()

    total_sessions = db.execute(
        "SELECT COUNT(*) FROM sessions WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    total_exercises = db.execute(
        "SELECT COUNT(*) FROM exercises WHERE user_id = ?", (user_id,)
    ).fetchone()[0]

    totals = db.execute(
        """
        SELECT COALESCE(SUM(es.reps), 0)             AS total_reps,
               COALESCE(SUM(es.duration_seconds), 0) AS total_seconds
        FROM sessions s
        JOIN session_exercises se ON se.session_id = s.id
        JOIN exercise_sets es     ON es.session_exercise_id = se.id
        WHERE s.user_id = ?
        """,
        (user_id,),
    ).fetchone()

    all_dates = db.execute(
        "SELECT DISTINCT session_date FROM sessions WHERE user_id = ? ORDER BY session_date DESC",
        (user_id,),
    ).fetchall()

    today = date.today()
    current_streak = 0
    longest_streak = 0
    if all_dates:
        dates = [date.fromisoformat(r["session_date"]) for r in all_dates]
        if dates[0] >= today - timedelta(days=1):
            streak = 0
            expected = today
            for d in dates:
                if streak == 0 and d == today - timedelta(days=1):
                    expected = d
                if d == expected:
                    streak += 1
                    expected -= timedelta(days=1)
                else:
                    break
            current_streak = streak
        streak = 1
        best = 1
        for i in range(1, len(dates)):
            if dates[i - 1] - dates[i] == timedelta(days=1):
                streak += 1
                best = max(best, streak)
            else:
                streak = 1
        longest_streak = best

    first_row = db.execute(
        "SELECT MIN(session_date) AS first FROM sessions WHERE user_id = ?", (user_id,)
    ).fetchone()
    first_session = first_row["first"] if first_row else None

    # Look up date_of_birth to compute age
    dob_row = db.execute(
        "SELECT date_of_birth FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    age = None
    if dob_row and dob_row["date_of_birth"]:
        try:
            from datetime import date as _date

            dob = _date.fromisoformat(dob_row["date_of_birth"])
            today = _date.today()
            age = (
                today.year
                - dob.year
                - ((today.month, today.day) < (dob.month, dob.day))
            )
        except ValueError:
            pass

    top_exercises = db.execute(
        """
        SELECT e.name,
               COALESCE(SUM(es.reps), 0)             AS total_reps,
               COALESCE(SUM(es.duration_seconds), 0) AS total_seconds,
               COUNT(DISTINCT s.id)                  AS session_count
        FROM exercises e
        JOIN session_exercises se ON se.exercise_id = e.id
        JOIN exercise_sets es     ON es.session_exercise_id = se.id
        JOIN sessions s           ON s.id = se.session_id
        WHERE e.user_id = ?
        GROUP BY e.id, e.name
        ORDER BY total_reps DESC, total_seconds DESC
        LIMIT 5
        """,
        (user_id,),
    ).fetchall()

    recent_sessions = db.execute(
        """
        SELECT s.id, s.session_date,
               GROUP_CONCAT(DISTINCT e.name)          AS exercise_names,
               COALESCE(SUM(es.reps), 0)              AS total_reps,
               COALESCE(SUM(es.duration_seconds), 0)  AS total_seconds
        FROM sessions s
        JOIN session_exercises se ON se.session_id = s.id
        JOIN exercise_sets es     ON es.session_exercise_id = se.id
        JOIN exercises e          ON e.id = se.exercise_id
        WHERE s.user_id = ?
        GROUP BY s.id
        ORDER BY s.session_date DESC, s.id DESC
        LIMIT 5
        """,
        (user_id,),
    ).fetchall()

    return dict(
        total_sessions=total_sessions,
        total_exercises=total_exercises,
        total_reps=totals["total_reps"],
        total_seconds=totals["total_seconds"],
        current_streak=current_streak,
        longest_streak=longest_streak,
        first_session=first_session,
        age=age,
        member_since=None,
        top_exercises=top_exercises,
        recent_sessions=recent_sessions,
    )


@bp.route("/settings")
@login_required
def settings():
    return render_template("settings.html", user=g.user, pw_open=False)


@bp.route("/settings/edit", methods=("GET", "POST"))
@login_required
def edit_profile():
    from app.db import get_db

    user_id = g.user["id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        date_of_birth = request.form.get("date_of_birth", "").strip()
        raw_weight = request.form.get("weight", "").strip()

        weight = None
        if raw_weight:
            try:
                weight = float(raw_weight.replace(",", "."))
                if weight <= 0:
                    raise ValueError
            except ValueError:
                flash("Weight must be a positive number.", "error")
                return render_template("settings.html", user=g.user, pw_open=False)

        db = get_db()
        db.execute(
            "UPDATE users SET name = ?, date_of_birth = ?, weight = ? WHERE id = ?",
            (name or None, date_of_birth or None, weight, user_id),
        )
        db.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("routes.settings"))

    return redirect(url_for("routes.settings"))


@bp.route("/settings/change-password", methods=("POST",))
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
        return render_template("settings.html", user=g.user, pw_open=True)

    flash("Password changed successfully.", "success")
    return redirect(url_for("routes.settings"))


@bp.route("/settings/clear-data", methods=("POST",))
@login_required
def clear_user_data():
    from werkzeug.security import check_password_hash

    from app.db import get_db

    password = request.form.get("confirm_clear_password", "")
    user = g.user

    if not check_password_hash(user["password_hash"], password):
        flash("Incorrect password. Data was not deleted.", "error")
        return redirect(url_for("routes.settings"))

    db = get_db()
    db.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
    db.execute("DELETE FROM exercises WHERE user_id = ?", (user["id"],))
    db.commit()

    flash("All your training data has been cleared.", "success")
    return redirect(url_for("routes.settings"))


@bp.route("/settings/delete", methods=("POST",))
@login_required
def delete_account():
    from werkzeug.security import check_password_hash

    from app.db import get_db

    password = request.form.get("confirm_delete_password", "")
    user = g.user

    if not check_password_hash(user["password_hash"], password):
        flash("Incorrect password. Account was not deleted.", "error")
        return redirect(url_for("routes.settings"))

    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    db.commit()

    session.clear()
    flash("Your account has been permanently deleted.", "success")
    return redirect(url_for("auth.register"))


@bp.route("/settings/export/<fmt>")
@login_required
def export_data(fmt):
    if fmt not in ("csv", "json"):
        abort(404)

    filename = f"sport_tracker_export_{date.today().isoformat()}.{fmt}"

    if fmt == "csv":
        response = make_response(export_csv(g.user["id"]))
        response.headers["Content-Type"] = "text/csv"
    else:
        response = make_response(export_json(g.user["id"]))
        response.headers["Content-Type"] = "application/json"

    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response
