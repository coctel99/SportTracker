"""Exercises DB queries."""

from app.db import get_db


def list_exercises(user_id: int):
    """Return all exercises for *user_id* ordered by name."""
    return get_db().execute(
        "SELECT * FROM exercises WHERE user_id = ? ORDER BY name ASC",
        (user_id,),
    ).fetchall()


def create_exercise(
    user_id: int,
    name: str,
    default_sets: int | None,
    default_reps: int | None,
) -> None:
    """Insert a new exercise row and commit.

    Raises:
        sqlite3.IntegrityError: if an exercise with the same name already exists
                                for this user.
    """
    db = get_db()
    db.execute(
        """
        INSERT INTO exercises (user_id, name, default_sets, default_reps)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, name, default_sets, default_reps),
    )
    db.commit()


def delete_exercise(exercise_id: int, user_id: int) -> None:
    """Delete the exercise owned by *user_id* and commit."""
    db = get_db()
    db.execute(
        "DELETE FROM exercises WHERE id = ? AND user_id = ?",
        (exercise_id, user_id),
    )
    db.commit()

