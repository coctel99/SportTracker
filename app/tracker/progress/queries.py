"""Progress DB queries."""

from app.db import get_db


def get_progress_summary(user_id: int):
    """Return all exercises with their cumulative rep counts for *user_id*."""
    return get_db().execute(
        """
        SELECT e.id, e.name,
               COALESCE(SUM(es.reps), 0) AS total_reps
        FROM exercises e
        LEFT JOIN session_exercises se ON se.exercise_id = e.id
        LEFT JOIN exercise_sets es ON es.session_exercise_id = se.id
        WHERE e.user_id = ?
        GROUP BY e.id, e.name
        ORDER BY e.name ASC
        """,
        (user_id,),
    ).fetchall()


def get_exercise_for_user(exercise_id: int, user_id: int):
    """Return the exercise row or None if it doesn't belong to *user_id*."""
    return get_db().execute(
        "SELECT id, name FROM exercises WHERE id = ? AND user_id = ?",
        (exercise_id, user_id),
    ).fetchone()


def get_chart_data(exercise_id: int, user_id: int) -> dict:
    """Return per-session sets and reps for charting.

    Returns a dict with keys ``labels``, ``sets``, ``reps``.
    """
    rows = get_db().execute(
        """
        SELECT s.session_date,
               COUNT(es.id)              AS sets_count,
               COALESCE(SUM(es.reps), 0) AS reps_total
        FROM sessions s
        JOIN session_exercises se ON se.session_id = s.id
        JOIN exercise_sets es     ON es.session_exercise_id = se.id
        WHERE s.user_id = ? AND se.exercise_id = ?
        GROUP BY s.session_date
        ORDER BY s.session_date ASC
        """,
        (user_id, exercise_id),
    ).fetchall()

    return {
        "labels": [row["session_date"] for row in rows],
        "sets":   [row["sets_count"]   for row in rows],
        "reps":   [row["reps_total"]   for row in rows],
    }

