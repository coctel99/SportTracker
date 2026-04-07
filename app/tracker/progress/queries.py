"""Progress DB queries."""

from app.db import get_db


def get_progress_summary(user_id: int):
    """Return all exercises with their cumulative rep and duration totals for *user_id*."""
    return (
        get_db()
        .execute(
            """
        SELECT e.id, e.name,
               COALESCE(SUM(es.reps), 0) AS total_reps,
               COALESCE(SUM(es.duration_seconds), 0) AS total_seconds
        FROM exercises e
        LEFT JOIN session_exercises se ON se.exercise_id = e.id
        LEFT JOIN exercise_sets es ON es.session_exercise_id = se.id
        WHERE e.user_id = ?
        GROUP BY e.id, e.name
        ORDER BY total_reps DESC, e.name ASC
        """,
            (user_id,),
        )
        .fetchall()
    )


def get_exercise_for_user(exercise_id: int, user_id: int):
    """Return the exercise row or None if it doesn't belong to *user_id*."""
    return (
        get_db()
        .execute(
            "SELECT id, name FROM exercises WHERE id = ? AND user_id = ?",
            (exercise_id, user_id),
        )
        .fetchone()
    )


def get_chart_data(exercise_id: int, user_id: int) -> dict:
    """Return per-session sets and reps for charting.

    Returns a dict with keys ``labels``, ``sets``, ``reps``.
    """
    rows = (
        get_db()
        .execute(
            """
        SELECT s.session_date,
               COUNT(es.id) AS sets_count,
               COALESCE(SUM(es.reps), 0) AS reps_total
        FROM sessions s
        JOIN session_exercises se ON se.session_id = s.id
        JOIN exercise_sets es     ON es.session_exercise_id = se.id
        WHERE s.user_id = ? AND se.exercise_id = ?
        GROUP BY s.session_date
        ORDER BY s.session_date ASC
        """,
            (user_id, exercise_id),
        )
        .fetchall()
    )

    return {
        "labels": [row["session_date"] for row in rows],
        "sets": [row["sets_count"] for row in rows],
        "reps": [row["reps_total"] for row in rows],
    }


def get_top_exercises_chart_data(user_id: int, limit: int = 5) -> dict:
    """Return a multi-series dataset for the top *limit* exercises by total reps.

    Returns a dict with:
      ``labels``   – sorted list of all session dates across those exercises
      ``series``   – list of {name, data} where data aligns with labels (0 for missing dates)
    """
    db = get_db()

    # Top exercises by total reps
    top = db.execute(
        """
        SELECT e.id, e.name, COALESCE(SUM(es.reps), 0) AS total_reps
        FROM exercises e
        LEFT JOIN session_exercises se ON se.exercise_id = e.id
        LEFT JOIN exercise_sets es ON es.session_exercise_id = se.id
        WHERE e.user_id = ?
        GROUP BY e.id, e.name
        ORDER BY total_reps DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()

    if not top:
        return {"labels": [], "series": []}

    top_ids = [row["id"] for row in top]

    # All (exercise_id, session_date, reps_total) rows for those exercises
    placeholders = ",".join("?" * len(top_ids))
    rows = db.execute(
        f"""
        SELECT se.exercise_id,
               s.session_date,
               COALESCE(SUM(es.reps), 0) AS reps_total
        FROM sessions s
        JOIN session_exercises se ON se.session_id = s.id
        JOIN exercise_sets es ON es.session_exercise_id = se.id
        WHERE s.user_id = ? AND se.exercise_id IN ({placeholders})
        GROUP BY se.exercise_id, s.session_date
        ORDER BY s.session_date ASC
        """,
        (user_id, *top_ids),
    ).fetchall()

    # Collect all unique dates
    all_dates = sorted({row["session_date"] for row in rows})

    # Build per-exercise lookup: {exercise_id: {date: reps}}
    lookup: dict[int, dict[str, int]] = {eid: {} for eid in top_ids}
    for row in rows:
        lookup[row["exercise_id"]][row["session_date"]] = row["reps_total"]

    series = [
        {
            "name": ex["name"],
            "data": [lookup[ex["id"]].get(d, 0) for d in all_dates],
        }
        for ex in top
    ]

    return {"labels": all_dates, "series": series}
