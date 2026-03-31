"""Tests for exercises routes."""

from tests.conftest import get_csrf_token, login, register


def register_and_login(client):
    register(client)
    login(client)


def test_add_exercise(client):
    register_and_login(client)

    response = client.post(
        "/exercises",
        data={
            "name": "Push Ups",
            "default_sets": "3",
            "default_reps": "12",
            "csrf_token": get_csrf_token(client, "/exercises"),
        },
        follow_redirects=True,
    )

    assert b"Push Ups" in response.data
    assert "3 sets" in response.data.decode()
    assert "12 reps" in response.data.decode()


def test_delete_exercise(client, db):
    register_and_login(client)
    client.post(
        "/exercises",
        data={"name": "Squats", "csrf_token": get_csrf_token(client, "/exercises")},
        follow_redirects=True,
    )

    exercise = db.execute("SELECT id FROM exercises WHERE name = 'Squats'").fetchone()
    response = client.post(
        f"/exercises/{exercise['id']}/delete",
        data={"csrf_token": get_csrf_token(client, "/exercises")},
        follow_redirects=True,
    )

    assert b"Squats" not in response.data


def test_add_exercise_rejects_missing_name(client):
    register_and_login(client)

    response = client.post(
        "/exercises",
        data={"name": "", "csrf_token": get_csrf_token(client, "/exercises")},
        follow_redirects=True,
    )

    assert b"Exercise name is required." in response.data


def test_add_exercise_rejects_invalid_defaults(client):
    register_and_login(client)

    response = client.post(
        "/exercises",
        data={
            "name": "Pull Ups",
            "default_sets": "0",
            "default_reps": "ten",
            "csrf_token": get_csrf_token(client, "/exercises"),
        },
        follow_redirects=True,
    )

    assert b"Default sets must be at least 1." in response.data


def test_duplicate_exercise_shows_error(client):
    register_and_login(client)
    csrf = get_csrf_token(client, "/exercises")
    client.post("/exercises", data={"name": "Plank", "csrf_token": csrf}, follow_redirects=True)

    response = client.post(
        "/exercises",
        data={"name": "Plank", "csrf_token": get_csrf_token(client, "/exercises")},
        follow_redirects=True,
    )

    assert b"already exists" in response.data
