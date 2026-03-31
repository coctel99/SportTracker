"""Tests for exercise CRUD."""

from tests.conftest import get_csrf_token, login, register


def register_and_login(client):
    register(client)
    login(client)


def _add_exercise(client, name="Squats", default_sets="", default_reps=""):
    return client.post(
        "/exercises",
        data={
            "name": name,
            "default_sets": default_sets,
            "default_reps": default_reps,
            "csrf_token": get_csrf_token(client, "/exercises"),
        },
        follow_redirects=True,
    )


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
    client.post(
        "/exercises", data={"name": "Plank", "csrf_token": csrf}, follow_redirects=True
    )

    response = client.post(
        "/exercises",
        data={"name": "Plank", "csrf_token": get_csrf_token(client, "/exercises")},
        follow_redirects=True,
    )

    assert b"already exists" in response.data


def test_edit_exercise_get(client, db):
    register_and_login(client)
    _add_exercise(client, "Squats")
    exercise_id = db.execute(
        "SELECT id FROM exercises WHERE name = 'Squats'"
    ).fetchone()["id"]

    response = client.get(f"/exercises/{exercise_id}/edit")

    assert response.status_code == 200
    assert b"Squats" in response.data


def test_edit_exercise_updates_name(client, db):
    register_and_login(client)
    _add_exercise(client, "Squats")
    exercise_id = db.execute(
        "SELECT id FROM exercises WHERE name = 'Squats'"
    ).fetchone()["id"]

    response = client.post(
        f"/exercises/{exercise_id}/edit",
        data={
            "name": "Barbell Squat",
            "default_sets": "4",
            "default_reps": "8",
            "csrf_token": get_csrf_token(client, f"/exercises/{exercise_id}/edit"),
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Barbell Squat" in response.data
    row = db.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
    assert row["name"] == "Barbell Squat"
    assert row["default_sets"] == 4
    assert row["default_reps"] == 8


def test_edit_exercise_rejects_empty_name(client, db):
    register_and_login(client)
    _add_exercise(client, "Squats")
    exercise_id = db.execute(
        "SELECT id FROM exercises WHERE name = 'Squats'"
    ).fetchone()["id"]

    response = client.post(
        f"/exercises/{exercise_id}/edit",
        data={
            "name": "",
            "csrf_token": get_csrf_token(client, f"/exercises/{exercise_id}/edit"),
        },
        follow_redirects=True,
    )

    assert b"Exercise name is required." in response.data
    # name must be unchanged in DB
    row = db.execute(
        "SELECT name FROM exercises WHERE id = ?", (exercise_id,)
    ).fetchone()
    assert row["name"] == "Squats"


def test_edit_exercise_rejects_duplicate_name(client, db):
    register_and_login(client)
    _add_exercise(client, "Squats")
    _add_exercise(client, "Lunges")
    exercise_id = db.execute(
        "SELECT id FROM exercises WHERE name = 'Squats'"
    ).fetchone()["id"]

    response = client.post(
        f"/exercises/{exercise_id}/edit",
        data={
            "name": "Lunges",
            "csrf_token": get_csrf_token(client, f"/exercises/{exercise_id}/edit"),
        },
        follow_redirects=True,
    )

    assert b"already exists" in response.data


def test_edit_exercise_rejects_invalid_sets(client, db):
    register_and_login(client)
    _add_exercise(client, "Squats")
    exercise_id = db.execute(
        "SELECT id FROM exercises WHERE name = 'Squats'"
    ).fetchone()["id"]

    response = client.post(
        f"/exercises/{exercise_id}/edit",
        data={
            "name": "Squats",
            "default_sets": "0",
            "csrf_token": get_csrf_token(client, f"/exercises/{exercise_id}/edit"),
        },
        follow_redirects=True,
    )

    assert b"at least 1" in response.data


def test_edit_exercise_404_for_other_user(client, db):
    register_and_login(client)

    response = client.get("/exercises/9999/edit")

    assert response.status_code == 404
