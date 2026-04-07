"""Sessions DB queries."""

from app.db import get_db


def get_exercises_for_user(user_id: int):
    """Return all exercises available for the session form."""
    return (
        get_db()
        .execute(
            """SELECT id, name, default_sets, default_reps,
                      default_duration_seconds, default_duration_unit
               FROM exercises WHERE user_id = ? ORDER BY name""",
            (user_id,),
        )
        .fetchall()
    )


def save_session(user_id: int, session_date: str, rows: list[tuple]) -> int:
    """Persist a complete training session atomically.

    *rows* is a list of ``(exercise_id, position, sets_data)`` tuples where
    ``sets_data`` is a list of ``(reps, duration_seconds)`` tuples
    (either value may be None, but not both).

    Returns the new session id.

    Raises ``Exception`` and rolls back on any DB error.
    """
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO sessions (user_id, session_date) VALUES (?, ?)",
            (user_id, session_date),
        )
        session_id = cur.lastrowid

        for exercise_id, position, sets_data in rows:
            se_cur = db.execute(
                """
                INSERT INTO session_exercises (session_id, exercise_id, position)
                VALUES (?, ?, ?)
                """,
                (session_id, exercise_id, position),
            )
            session_exercise_id = se_cur.lastrowid

            for set_number, (reps, duration_seconds) in enumerate(sets_data, start=1):
                db.execute(
                    """
                    INSERT INTO exercise_sets (session_exercise_id, set_number, reps, duration_seconds)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_exercise_id, set_number, reps, duration_seconds),
                )

        db.commit()
        return session_id
    except Exception:
        db.rollback()
        raise


def get_session_for_user(session_id: int, user_id: int):
    """Return the session row if it belongs to *user_id*, else None."""
    return (
        get_db()
        .execute(
            "SELECT id, session_date FROM sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        )
        .fetchone()
    )


def get_session_detail(session_id: int) -> list:
    """Return a list of exercises with their sets for a session.

    Each row has: exercise_name, set_number, reps, duration_seconds.
    Results are ordered by position then set_number.
    """
    return (
        get_db()
        .execute(
            """
        SELECT e.name AS exercise_name,
               se.position,
               es.set_number,
               es.reps,
               es.duration_seconds
        FROM session_exercises se
        JOIN exercises e ON e.id = se.exercise_id
        JOIN exercise_sets es ON es.session_exercise_id = se.id
        WHERE se.session_id = ?
        ORDER BY se.position ASC, es.set_number ASC
        """,
            (session_id,),
        )
        .fetchall()
    )


def delete_session(session_id: int, user_id: int) -> None:
    """Delete a session owned by *user_id* and commit."""
    db = get_db()
    db.execute(
        "DELETE FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    db.commit()


def update_session(
    session_id: int, user_id: int, session_date: str, rows: list[tuple]
) -> None:
    """Replace all exercises/sets for an existing session atomically.

    Deletes the existing session_exercises (cascades to exercise_sets) and
    re-inserts from *rows*, same format as save_session.
    """
    db = get_db()
    try:
        db.execute(
            "UPDATE sessions SET session_date = ? WHERE id = ? AND user_id = ?",
            (session_date, session_id, user_id),
        )
        db.execute(
            "DELETE FROM session_exercises WHERE session_id = ?",
            (session_id,),
        )
        for exercise_id, position, sets_data in rows:
            se_cur = db.execute(
                """
                INSERT INTO session_exercises (session_id, exercise_id, position)
                VALUES (?, ?, ?)
                """,
                (session_id, exercise_id, position),
            )
            session_exercise_id = se_cur.lastrowid
            for set_number, (reps, duration_seconds) in enumerate(sets_data, start=1):
                db.execute(
                    """
                    INSERT INTO exercise_sets (session_exercise_id, set_number, reps, duration_seconds)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_exercise_id, set_number, reps, duration_seconds),
                )
        db.commit()
    except Exception:
        db.rollback()
        raise


def get_session_detail_for_edit(session_id: int) -> list:
    """Return exercises with their set data grouped, for pre-filling the edit form."""
    rows = (
        get_db()
        .execute(
            """
        SELECT se.exercise_id, e.name AS exercise_name,
               se.position, es.reps, es.duration_seconds
        FROM session_exercises se
        JOIN exercises e ON e.id = se.exercise_id
        JOIN exercise_sets es ON es.session_exercise_id = se.id
        WHERE se.session_id = ?
        ORDER BY se.position ASC, es.set_number ASC
        """,
            (session_id,),
        )
        .fetchall()
    )
    # group into [{exercise_id, name, sets:[(reps, duration_seconds),...]}]
    grouped = []
    for row in rows:
        if not grouped or grouped[-1]["exercise_id"] != row["exercise_id"]:
            grouped.append(
                {
                    "exercise_id": row["exercise_id"],
                    "name": row["exercise_name"],
                    "sets": [],
                }
            )
        grouped[-1]["sets"].append((row["reps"], row["duration_seconds"]))
    return grouped


def get_sessions_for_day(user_id: int, session_date: str) -> list[dict]:
    """Return all sessions for *user_id* on *session_date*, each with their exercises.

    Returns a list of dicts::

        [{"id": int, "session_date": str,
          "exercises": [{"name": str, "total_reps": int}, ...]}, ...]
    """
    db = get_db()
    session_rows = db.execute(
        """
        SELECT id, session_date
        FROM sessions
        WHERE user_id = ? AND session_date = ?
        ORDER BY id ASC
        """,
        (user_id, session_date),
    ).fetchall()

    result = []
    for s in session_rows:
        exercises = db.execute(
            """
            SELECT e.name,
                   COALESCE(SUM(es.reps), 0) AS total_reps,
                   COUNT(es.id)              AS total_sets
            FROM session_exercises se
            JOIN exercises e  ON e.id  = se.exercise_id
            JOIN exercise_sets es ON es.session_exercise_id = se.id
            WHERE se.session_id = ?
            GROUP BY e.id, e.name
            ORDER BY se.position ASC
            """,
            (s["id"],),
        ).fetchall()
        result.append(
            {
                "id": s["id"],
                "session_date": s["session_date"],
                "exercises": [dict(e) for e in exercises],
            }
        )
    return result
