"""Dashboard DB queries."""

from datetime import date, timedelta

from app.db import get_db


def get_dashboard_stats(user_id: int) -> dict:
    """Return all stats needed to render the dashboard."""
    db = get_db()
    today = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()

    sessions_this_week = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM sessions
        WHERE user_id = ?
          AND session_date >= ?
        """,
        (user_id, week_start),
    ).fetchone()["count"]

    recent_sessions = db.execute(
        """
        SELECT id, session_date
        FROM sessions
        WHERE user_id = ?
        ORDER BY session_date DESC, id DESC
        LIMIT 5
        """,
        (user_id,),
    ).fetchall()

    total_reps_today = db.execute(
        """
        SELECT COALESCE(SUM(es.reps), 0) AS reps
        FROM sessions s
        JOIN session_exercises se ON se.session_id = s.id
        JOIN exercise_sets es ON es.session_exercise_id = se.id
        WHERE s.user_id = ? AND s.session_date = ?
        """,
        (user_id, today.isoformat()),
    ).fetchone()["reps"]

    return {
        "sessions_this_week": sessions_this_week,
        "recent_sessions": recent_sessions,
        "total_reps_today": total_reps_today,
    }

