"""Progress DB queries."""

from app.db import get_db


def get_progress_summary(user_id: int):
    """Return all exercises with their cumulative rep and duration totals for *user_id*.

    Each row also carries ``is_time_based`` (1/0): exercises that have logged
    duration but zero reps are considered time-based and should be sorted /
    displayed by time rather than by reps.
    """
    return (
        get_db()
        .execute(
            """
        SELECT e.id, e.name,
               COALESCE(SUM(es.reps), 0)             AS total_reps,
               COALESCE(SUM(es.duration_seconds), 0) AS total_seconds,
               CASE
                 WHEN COALESCE(SUM(es.reps), 0) = 0
                  AND COALESCE(SUM(es.duration_seconds), 0) > 0
                 THEN 1 ELSE 0
               END AS is_time_based
        FROM exercises e
        LEFT JOIN session_exercises se ON se.exercise_id = e.id
        LEFT JOIN exercise_sets es ON es.session_exercise_id = se.id
        WHERE e.user_id = ?
        GROUP BY e.id, e.name
        ORDER BY total_reps DESC, total_seconds DESC, e.name ASC
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
    """Return per-session sets, reps and duration for charting.

    Returns a dict with keys ``labels``, ``sets``, ``reps``, ``duration_seconds``,
    and ``is_time_based`` (True when the exercise has duration but no reps logged).
    """
    rows = (
        get_db()
        .execute(
            """
        SELECT s.session_date,
               COUNT(es.id)                          AS sets_count,
               COALESCE(SUM(es.reps), 0)             AS reps_total,
               COALESCE(SUM(es.duration_seconds), 0) AS duration_total
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

    reps_list = [row["reps_total"] for row in rows]
    duration_list = [row["duration_total"] for row in rows]
    is_time_based = sum(reps_list) == 0 and sum(duration_list) > 0

    return {
        "labels": [row["session_date"] for row in rows],
        "sets": [row["sets_count"] for row in rows],
        "reps": reps_list,
        "duration_seconds": duration_list,
        "is_time_based": is_time_based,
    }


def get_top_exercises_chart_data(user_id: int, limit: int = 5) -> dict:
    """Return a multi-series dataset for the top *limit* exercises.

    Exercises are ranked by total reps first; purely time-based exercises
    (zero reps) are ranked by total duration instead so they appear in the chart.

    Each series carries ``is_time_based`` so the chart can label the y-axis
    value correctly (minutes for time-based, reps otherwise).

    Returns a dict with:
      ``labels``   – sorted list of all session dates across those exercises
      ``series``   – list of {name, is_time_based, data} where data aligns with
                     labels (0 for missing dates); values are reps for reps-based
                     and *minutes* (rounded) for time-based exercises.
    """
    db = get_db()

    # Top exercises – rank by reps; fall back to duration for time-only exercises
    top = db.execute(
        """
        SELECT e.id, e.name,
               COALESCE(SUM(es.reps), 0)             AS total_reps,
               COALESCE(SUM(es.duration_seconds), 0) AS total_seconds,
               CASE
                 WHEN COALESCE(SUM(es.reps), 0) = 0
                  AND COALESCE(SUM(es.duration_seconds), 0) > 0
                 THEN 1 ELSE 0
               END AS is_time_based
        FROM exercises e
        LEFT JOIN session_exercises se ON se.exercise_id = e.id
        LEFT JOIN exercise_sets es ON es.session_exercise_id = se.id
        WHERE e.user_id = ?
        GROUP BY e.id, e.name
        ORDER BY total_reps DESC, total_seconds DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()

    if not top:
        return {"labels": [], "series": []}

    top_ids = [row["id"] for row in top]

    # All (exercise_id, session_date, reps_total, duration_total) rows
    placeholders = ",".join("?" * len(top_ids))
    rows = db.execute(
        f"""
        SELECT se.exercise_id,
               s.session_date,
               COALESCE(SUM(es.reps), 0)             AS reps_total,
               COALESCE(SUM(es.duration_seconds), 0) AS duration_total
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

    # Build per-exercise lookup: {exercise_id: {date: (reps, duration_seconds)}}
    lookup: dict[int, dict[str, tuple]] = {eid: {} for eid in top_ids}
    for row in rows:
        lookup[row["exercise_id"]][row["session_date"]] = (
            row["reps_total"],
            row["duration_total"],
        )

    series = []
    for ex in top:
        is_time_based = bool(ex["is_time_based"])
        reps_points = []
        dur_points = []
        for d in all_dates:
            reps, dur = lookup[ex["id"]].get(d, (0, 0))
            reps_points.append(reps)
            dur_points.append(dur)
        series.append(
            {
                "name": ex["name"],
                "is_time_based": is_time_based,
                # For reps-based: reps values; for time-based: raw seconds
                "data": dur_points if is_time_based else reps_points,
                "max_seconds": max(dur_points) if is_time_based else 0,
            }
        )

    return {"labels": all_dates, "series": series}
