"""Export user data as CSV or JSON."""

import csv
import io
import json

from app.db import get_db


def export_csv(user_id: int) -> str:
    rows = _fetch_rows(user_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "exercise", "set_number", "reps", "duration_seconds"])
    for r in rows:
        writer.writerow(
            [
                r["session_date"],
                r["exercise"],
                r["set_number"],
                r["reps"],
                r["duration_seconds"],
            ]
        )
    return output.getvalue()


def export_json(user_id: int) -> str:
    rows = _fetch_rows(user_id)
    data: dict = {}
    for r in rows:
        set_entry: dict = {}
        if r["reps"] is not None:
            set_entry["reps"] = r["reps"]
        if r["duration_seconds"] is not None:
            set_entry["duration_seconds"] = r["duration_seconds"]
        data.setdefault(r["session_date"], {}).setdefault(r["exercise"], []).append(
            set_entry
        )
    return json.dumps(data, indent=2)


def _fetch_rows(user_id: int):
    return (
        get_db()
        .execute(
            """
        SELECT
            s.session_date,
            e.name  AS exercise,
            se.position,
            es.set_number,
            es.reps,
            es.duration_seconds
        FROM sessions s
        JOIN session_exercises se ON se.session_id = s.id
        JOIN exercises e          ON e.id = se.exercise_id
        JOIN exercise_sets es     ON es.session_exercise_id = se.id
        WHERE s.user_id = ?
        ORDER BY s.session_date, se.position, es.set_number
        """,
            (user_id,),
        )
        .fetchall()
    )
