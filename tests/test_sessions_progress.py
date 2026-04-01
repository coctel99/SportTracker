"""Tests for session logging and progress API routes."""

import json

from tests.conftest import get_csrf_token, register


def register_login_add_exercise(client, db):
    register(client)
    client.post(
        "/exercises",
        data={"name": "Bench", "csrf_token": get_csrf_token(client, "/exercises")},
        follow_redirects=True,
    )
    return db.execute("SELECT id FROM exercises WHERE name = 'Bench'").fetchone()["id"]


def test_log_session_and_progress_api(client, db):
    exercise_id = register_login_add_exercise(client, db)

    response = client.post(
        "/sessions/new",
        data={
            "session_date": "2026-03-31",
            "exercise_id[]": [str(exercise_id)],
            "reps[]": ["10,8,7"],
            "csrf_token": get_csrf_token(client, "/sessions/new"),
        },
        follow_redirects=True,
    )
    assert b"Dashboard" in response.data

    progress_response = client.get(f"/api/progress/{exercise_id}")
    payload = json.loads(progress_response.data)

    assert progress_response.status_code == 200
    assert payload["labels"] == ["2026-03-31"]
    assert payload["sets"] == [3]
    assert payload["reps"] == [25]


def test_log_session_rejects_invalid_date(client, db):
    exercise_id = register_login_add_exercise(client, db)

    response = client.post(
        "/sessions/new",
        data={
            "session_date": "2026-02-31",
            "exercise_id[]": [str(exercise_id)],
            "reps[]": ["10,8,7"],
            "csrf_token": get_csrf_token(client, "/sessions/new"),
        },
        follow_redirects=True,
    )

    sessions_count = db.execute("SELECT COUNT(*) AS count FROM sessions").fetchone()[
        "count"
    ]
    assert b"Session date must be a valid date." in response.data
    assert sessions_count == 0


def test_log_session_rejects_invalid_reps(client, db):
    exercise_id = register_login_add_exercise(client, db)

    response = client.post(
        "/sessions/new",
        data={
            "session_date": "2026-03-31",
            "exercise_id[]": [str(exercise_id)],
            "reps[]": ["10,abc,7"],
            "csrf_token": get_csrf_token(client, "/sessions/new"),
        },
        follow_redirects=True,
    )

    sessions_count = db.execute("SELECT COUNT(*) AS count FROM sessions").fetchone()[
        "count"
    ]
    assert b"Reps must be comma-separated whole numbers." in response.data
    assert sessions_count == 0


def test_log_session_rejects_no_rows(client, db):
    register_login_add_exercise(client, db)

    response = client.post(
        "/sessions/new",
        data={
            "session_date": "2026-03-31",
            "csrf_token": get_csrf_token(client, "/sessions/new"),
        },
        follow_redirects=True,
    )

    assert b"Add at least one exercise row." in response.data


def test_progress_detail_404_for_other_user(client, db):
    """A user cannot view another user's exercise progress."""
    register_login_add_exercise(client, db)
    response = client.get("/progress/9999")
    assert response.status_code == 404


def test_api_progress_404_for_other_user(client, db):
    register_login_add_exercise(client, db)
    response = client.get("/api/progress/9999")
    assert response.status_code == 404
