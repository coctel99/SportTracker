"""Exercises DB queries."""

from app.db import get_db


def list_exercises(user_id: int):
    """Return all exercises for *user_id* ordered by name."""
    return (
        get_db()
        .execute(
            "SELECT * FROM exercises WHERE user_id = ? ORDER BY name ASC",
            (user_id,),
        )
        .fetchall()
    )


def create_exercise(
    user_id: int,
    name: str,
    default_sets: int | None,
    default_reps: int | None,
    default_duration_seconds: int | None = None,
    default_duration_unit: str | None = None,
) -> None:
    """Insert a new exercise row and commit.

    Raises:
        sqlite3.IntegrityError: if an exercise with the same name already exists
                                for this user.
    """
    db = get_db()
    db.execute(
        """
        INSERT INTO exercises (user_id, name, default_sets, default_reps,
                               default_duration_seconds, default_duration_unit)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            name,
            default_sets,
            default_reps,
            default_duration_seconds,
            default_duration_unit,
        ),
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


def update_exercise(
    exercise_id: int,
    user_id: int,
    name: str,
    default_sets: int | None,
    default_reps: int | None,
    default_duration_seconds: int | None = None,
    default_duration_unit: str | None = None,
) -> None:
    """Update an existing exercise owned by *user_id* and commit.

    Raises:
        sqlite3.IntegrityError: if another exercise with the same name already exists.
    """
    db = get_db()
    db.execute(
        """
        UPDATE exercises
        SET name = ?, default_sets = ?, default_reps = ?,
            default_duration_seconds = ?, default_duration_unit = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            name,
            default_sets,
            default_reps,
            default_duration_seconds,
            default_duration_unit,
            exercise_id,
            user_id,
        ),
    )
    db.commit()


def get_exercise(exercise_id: int, user_id: int):
    """Return the exercise row owned by *user_id*, or None."""
    return (
        get_db()
        .execute(
            "SELECT * FROM exercises WHERE id = ? AND user_id = ?",
            (exercise_id, user_id),
        )
        .fetchone()
    )
