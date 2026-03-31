"""All application HTTP routes in one place.

Each handler is deliberately thin: read request data → call tracker logic →
flash / redirect / render.  No SQL and no business logic lives here.
"""

import sqlite3
from datetime import date

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

from app.auth import login_required
from app.tracker.dashboard.queries import get_dashboard_stats
from app.tracker.exercises.queries import create_exercise, delete_exercise, list_exercises
from app.tracker.sessions.forms import parse_optional_int, parse_reps_list, parse_session_date
from app.tracker.sessions.queries import (
    delete_session,
    get_exercises_for_user,
    get_session_detail,
    get_session_for_user,
    save_session,
)
from app.tracker.progress.queries import get_chart_data, get_exercise_for_user, get_progress_summary

bp = Blueprint("routes", __name__)


# ── Root ──────────────────────────────────────────────────────────────────────

@bp.route("/")
def index():
    if g.user is None:
        return redirect(url_for("auth.login"))
    return redirect(url_for("routes.dashboard"))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@bp.route("/dashboard")
@login_required
def dashboard():
    stats = get_dashboard_stats(g.user["id"])
    return render_template("dashboard.html", **stats)


# ── Exercises ─────────────────────────────────────────────────────────────────

@bp.route("/exercises", methods=("GET", "POST"))
@login_required
def exercises():
    user_id = g.user["id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        raw_sets = request.form.get("default_sets", "").strip()
        raw_reps = request.form.get("default_reps", "").strip()

        if not name:
            flash("Exercise name is required.")
        else:
            try:
                default_sets = parse_optional_int(raw_sets, "Default sets", minimum=1)
                default_reps = parse_optional_int(raw_reps, "Default reps", minimum=0)
                create_exercise(user_id, name, default_sets, default_reps)
                return redirect(url_for("routes.exercises"))
            except ValueError as exc:
                flash(str(exc))
            except sqlite3.IntegrityError:
                flash("Exercise with this name already exists.")

    items = list_exercises(user_id)
    return render_template("exercises.html", exercises=items)


@bp.route("/exercises/<int:exercise_id>/delete", methods=("POST",))
@login_required
def delete_exercise_view(exercise_id):
    delete_exercise(exercise_id, g.user["id"])
    return redirect(url_for("routes.exercises"))


# ── Sessions ──────────────────────────────────────────────────────────────────

@bp.route("/sessions/new", methods=("GET", "POST"))
@login_required
def new_session():
    user_id = g.user["id"]
    today = date.today().isoformat()
    exercises_list = get_exercises_for_user(user_id)

    def _render():
        return render_template("session_new.html", exercises=exercises_list, today=today)

    if request.method == "POST":
        try:
            session_date = parse_session_date(request.form.get("session_date", ""))
        except ValueError as exc:
            flash(str(exc))
            return _render()

        exercise_ids = request.form.getlist("exercise_id[]")
        reps_raw = request.form.getlist("reps[]")
        allowed_ids = {row["id"] for row in exercises_list}
        rows = []

        if not exercise_ids:
            flash("Add at least one exercise row.")
            return _render()

        for idx, raw_id in enumerate(exercise_ids):
            raw_id = raw_id.strip()
            raw_reps = reps_raw[idx] if idx < len(reps_raw) else ""

            if not raw_id and not raw_reps.strip():
                continue

            if not raw_id:
                flash("Each session row must include an exercise.")
                return _render()

            try:
                exercise_id = int(raw_id)
            except ValueError:
                flash("Please choose a valid exercise.")
                return _render()

            if exercise_id not in allowed_ids:
                flash("Please choose a valid exercise.")
                return _render()

            try:
                reps_list = parse_reps_list(raw_reps)
            except ValueError as exc:
                flash(str(exc))
                return _render()

            rows.append((exercise_id, idx, reps_list))

        if not rows:
            flash("Add at least one complete exercise row.")
            return _render()

        try:
            save_session(user_id, session_date, rows)
        except Exception:
            flash("An error occurred while saving the session. Please try again.")
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


@bp.route("/sessions/<int:session_id>/delete", methods=("POST",))
@login_required
def delete_session_view(session_id):
    sess = get_session_for_user(session_id, g.user["id"])
    if sess is None:
        abort(404)
    delete_session(session_id, g.user["id"])
    flash("Session deleted.")
    return redirect(url_for("routes.dashboard"))


# ── Progress ──────────────────────────────────────────────────────────────────

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

