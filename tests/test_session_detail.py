"""Tests for session detail view and session deletion."""

from tests.conftest import get_csrf_token, login, register


def register_login_add_session(client, db):
    """Register, login, add an exercise, log a session; return session id."""
    register(client)
    login(client)
    client.post(
        "/exercises",
        data={"name": "Deadlift", "csrf_token": get_csrf_token(client, "/exercises")},
        follow_redirects=True,
    )
    exercise_id = db.execute(
        "SELECT id FROM exercises WHERE name = 'Deadlift'"
    ).fetchone()["id"]
    client.post(
        "/sessions/new",
        data={
            "session_date": "2026-03-31",
            "exercise_id[]": [str(exercise_id)],
            "reps[]": ["5,5,5"],
            "csrf_token": get_csrf_token(client, "/sessions/new"),
        },
        follow_redirects=True,
    )
    return db.execute("SELECT id FROM sessions").fetchone()["id"]


def test_session_detail_shows_exercises(client, db):
    session_id = register_login_add_session(client, db)

    response = client.get(f"/sessions/{session_id}")

    assert response.status_code == 200
    assert b"Deadlift" in response.data
    assert b"2026-03-31" in response.data
    # Each set value (5) should appear
    assert b"5" in response.data


def test_session_detail_shows_set_count(client, db):
    session_id = register_login_add_session(client, db)

    response = client.get(f"/sessions/{session_id}")

    assert b"3 sets" in response.data


def test_session_detail_shows_total_reps(client, db):
    session_id = register_login_add_session(client, db)

    response = client.get(f"/sessions/{session_id}")

    # 5+5+5 = 15 total reps
    assert b"15" in response.data


def test_session_detail_404_for_other_user(client, db):
    register_login_add_session(client, db)

    response = client.get("/sessions/9999")

    assert response.status_code == 404


def test_dashboard_links_to_session_detail(client, db):
    session_id = register_login_add_session(client, db)

    response = client.get("/dashboard")

    assert f"/sessions/{session_id}".encode() in response.data


def test_delete_session(client, db):
    session_id = register_login_add_session(client, db)

    csrf = get_csrf_token(client, f"/sessions/{session_id}")
    response = client.post(
        f"/sessions/{session_id}/delete",
        data={"csrf_token": csrf},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Session deleted." in response.data
    count = db.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"]
    assert count == 0


def test_delete_session_404_for_other_user(client, db):
    register_login_add_session(client, db)

    csrf = get_csrf_token(client, "/dashboard")
    response = client.post(
        "/sessions/9999/delete",
        data={"csrf_token": csrf},
    )

    assert response.status_code == 404

