"""Sessions DB queries."""

from app.db import get_db


def get_exercises_for_user(user_id: int):
    """Return all exercises available for the session form."""
    return get_db().execute(
        "SELECT id, name, default_reps FROM exercises WHERE user_id = ? ORDER BY name",
        (user_id,),
    ).fetchall()


def save_session(user_id: int, session_date: str, rows: list[tuple]) -> int:
    """Persist a complete training session atomically.

    *rows* is a list of ``(exercise_id, position, reps_list)`` tuples where
    ``reps_list`` is a list of non-negative integers (one per set).

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

        for exercise_id, position, reps_list in rows:
            se_cur = db.execute(
                """
                INSERT INTO session_exercises (session_id, exercise_id, position)
                VALUES (?, ?, ?)
                """,
                (session_id, exercise_id, position),
            )
            session_exercise_id = se_cur.lastrowid

            for set_number, reps in enumerate(reps_list, start=1):
                db.execute(
                    """
                    INSERT INTO exercise_sets (session_exercise_id, set_number, reps)
                    VALUES (?, ?, ?)
                    """,
                    (session_exercise_id, set_number, reps),
                )

        db.commit()
        return session_id
    except Exception:
        db.rollback()
        raise


def get_session_for_user(session_id: int, user_id: int):
    """Return the session row if it belongs to *user_id*, else None."""
    return get_db().execute(
        "SELECT id, session_date FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()


def get_session_detail(session_id: int) -> list:
    """Return a list of exercises with their sets for a session.

    Each row has: exercise_name, set_number, reps.
    Results are ordered by position then set_number.
    """
    return get_db().execute(
        """
        SELECT e.name AS exercise_name,
               se.position,
               es.set_number,
               es.reps
        FROM session_exercises se
        JOIN exercises e ON e.id = se.exercise_id
        JOIN exercise_sets es ON es.session_exercise_id = se.id
        WHERE se.session_id = ?
        ORDER BY se.position ASC, es.set_number ASC
        """,
        (session_id,),
    ).fetchall()


def delete_session(session_id: int, user_id: int) -> None:
    """Delete a session owned by *user_id* and commit."""
    db = get_db()
    db.execute(
        "DELETE FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    db.commit()
