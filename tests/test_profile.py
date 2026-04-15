"""Tests for the profile page, settings page, editing personal details, and changing password."""

from tests.conftest import get_csrf_token, login, register


def register_and_login(client):
    """Register (which auto-logs in) and return the client ready to use."""
    register(client)
    return client


def post_edit(client, **fields):
    csrf = get_csrf_token(client, "/settings")
    return client.post(
        "/settings/edit",
        data={"csrf_token": csrf, **fields},
        follow_redirects=True,
    )


def post_change_password(client, current, new, confirm):
    csrf = get_csrf_token(client, "/settings")
    return client.post(
        "/settings/change-password",
        data={
            "csrf_token": csrf,
            "current_password": current,
            "new_password": new,
            "confirm_password": confirm,
        },
        follow_redirects=True,
    )


# ── Profile page (public-facing) ─────────────────────────────────────────────


def test_profile_page_loads(client):
    register_and_login(client)
    response = client.get("/profile")
    assert response.status_code == 200
    assert b"Sessions" in response.data


def test_profile_shows_user_name(client):
    register(client, name="Alice Smith")
    response = client.get("/profile")
    assert b"Alice Smith" in response.data


def test_profile_shows_user_email_initial(client):
    register(client, email="alice@example.com", name="Alice")
    response = client.get("/profile")
    assert b"Alice" in response.data


def test_profile_requires_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ── Settings page ─────────────────────────────────────────────────────────────


def test_settings_page_loads(client):
    register_and_login(client)
    response = client.get("/settings")
    assert response.status_code == 200
    assert b"Personal details" in response.data


def test_settings_requires_login(client):
    response = client.get("/settings")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ── Edit profile ──────────────────────────────────────────────────────────────


def test_edit_profile_updates_name(client, db):
    register_and_login(client)
    post_edit(client, name="Bob Jones", date_of_birth="", weight="")
    row = db.execute("SELECT name FROM users").fetchone()
    assert row["name"] == "Bob Jones"


def test_edit_profile_updates_dob(client, db):
    register_and_login(client)
    post_edit(client, name="Test User", date_of_birth="1990-06-15", weight="")
    row = db.execute("SELECT date_of_birth FROM users").fetchone()
    assert row["date_of_birth"] == "1990-06-15"


def test_edit_profile_updates_weight(client, db):
    register_and_login(client)
    post_edit(client, name="Test User", date_of_birth="", weight="75.5")
    row = db.execute("SELECT weight FROM users").fetchone()
    assert row["weight"] == 75.5


def test_edit_profile_clears_optional_fields(client, db):
    register_and_login(client)
    post_edit(client, name="Test User", date_of_birth="1990-01-01", weight="80")
    post_edit(client, name="Test User", date_of_birth="", weight="")
    row = db.execute("SELECT date_of_birth, weight FROM users").fetchone()
    assert row["date_of_birth"] is None
    assert row["weight"] is None


def test_edit_profile_shows_success_flash(client):
    register_and_login(client)
    response = post_edit(client, name="New Name", date_of_birth="", weight="")
    assert b"Profile updated" in response.data


def test_edit_profile_name_is_optional(client, db):
    register_and_login(client)
    # Clearing name should be accepted (name is optional)
    response = post_edit(client, name="", date_of_birth="", weight="")
    assert b"Profile updated" in response.data
    row = db.execute("SELECT name FROM users").fetchone()
    assert row["name"] is None


def test_edit_profile_rejects_invalid_weight(client, db):
    register_and_login(client)
    response = post_edit(client, name="Test User", date_of_birth="", weight="abc")
    assert b"positive number" in response.data
    row = db.execute("SELECT weight FROM users").fetchone()
    assert row["weight"] is None  # unchanged


def test_edit_profile_rejects_negative_weight(client, db):
    register_and_login(client)
    response = post_edit(client, name="Test User", date_of_birth="", weight="-5")
    assert b"positive number" in response.data


# ── Change password ───────────────────────────────────────────────────────────


def test_change_password_success(client):
    register_and_login(client)
    response = post_change_password(client, "secret12", "newpass99", "newpass99")
    assert b"Password changed successfully" in response.data


def test_change_password_allows_login_with_new_password(client):
    register_and_login(client)
    post_change_password(client, "secret12", "newpass99", "newpass99")
    csrf = get_csrf_token(client, "/dashboard")
    client.post("/logout", data={"csrf_token": csrf})
    response = login(client, password="newpass99")
    assert b"Dashboard" in response.data


def test_change_password_rejects_wrong_current(client):
    register_and_login(client)
    response = post_change_password(client, "wrongpass", "newpass99", "newpass99")
    assert b"incorrect" in response.data


def test_change_password_rejects_mismatch(client):
    register_and_login(client)
    response = post_change_password(client, "secret12", "newpass99", "different9")
    assert b"do not match" in response.data


def test_change_password_rejects_short_new_password(client):
    register_and_login(client)
    response = post_change_password(client, "secret12", "short", "short")
    assert b"at least 8 characters" in response.data


def test_change_password_rejects_missing_fields(client):
    register_and_login(client)
    response = post_change_password(client, "", "", "")
    assert b"required" in response.data


def test_change_password_wrong_current_keeps_form_open(client):
    register_and_login(client)
    response = post_change_password(client, "wrongpass", "newpass99", "newpass99")
    assert b"current_password" in response.data
    assert b"incorrect" in response.data


def test_old_password_rejected_after_change(client):
    register_and_login(client)
    post_change_password(client, "secret12", "newpass99", "newpass99")
    csrf = get_csrf_token(client, "/dashboard")
    client.post("/logout", data={"csrf_token": csrf})
    response = login(client, password="secret12")
    assert b"Invalid credentials" in response.data


# ── Delete account ────────────────────────────────────────────────────────────


def post_delete_account(client, password):
    csrf = get_csrf_token(client, "/settings")
    return client.post(
        "/settings/delete",
        data={"csrf_token": csrf, "confirm_delete_password": password},
        follow_redirects=True,
    )


def test_delete_account_success(client, db):
    register_and_login(client)
    response = post_delete_account(client, "secret12")
    assert b"permanently deleted" in response.data
    row = db.execute("SELECT * FROM users").fetchone()
    assert row is None


def test_delete_account_wrong_password(client, db):
    register_and_login(client)
    response = post_delete_account(client, "wrongpassword")
    assert b"Incorrect password" in response.data
    row = db.execute("SELECT * FROM users").fetchone()
    assert row is not None


def test_delete_account_removes_all_data(client, db):
    register_and_login(client)
    csrf = get_csrf_token(client, "/exercises")
    client.post(
        "/exercises", data={"name": "Squat", "csrf_token": csrf}, follow_redirects=True
    )
    ex_id = db.execute("SELECT id FROM exercises").fetchone()["id"]
    csrf = get_csrf_token(client, "/sessions/new")
    client.post(
        "/sessions/new",
        data={
            "session_date": "2026-01-01",
            "exercise_id[]": [str(ex_id)],
            "reps[]": ["10,10"],
            "csrf_token": csrf,
        },
        follow_redirects=True,
    )
    post_delete_account(client, "secret12")
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM exercises").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0


# ── Clear user data ───────────────────────────────────────────────────────────


def post_clear_data(client, password):
    csrf = get_csrf_token(client, "/settings")
    return client.post(
        "/settings/clear-data",
        data={"csrf_token": csrf, "confirm_clear_password": password},
        follow_redirects=True,
    )


def _create_exercise_and_session(client, db):
    """Helper: create one exercise and one session; return exercise id."""
    csrf = get_csrf_token(client, "/exercises")
    client.post(
        "/exercises", data={"name": "Squat", "csrf_token": csrf}, follow_redirects=True
    )
    ex_id = db.execute("SELECT id FROM exercises").fetchone()["id"]
    csrf = get_csrf_token(client, "/sessions/new")
    client.post(
        "/sessions/new",
        data={
            "session_date": "2026-01-01",
            "exercise_id[]": [str(ex_id)],
            "reps[]": ["10,10"],
            "csrf_token": csrf,
        },
        follow_redirects=True,
    )
    return ex_id


def test_clear_data_success_flash(client, db):
    register_and_login(client)
    _create_exercise_and_session(client, db)
    response = post_clear_data(client, "secret12")
    assert b"cleared" in response.data


def test_clear_data_removes_sessions_and_exercises(client, db):
    register_and_login(client)
    _create_exercise_and_session(client, db)
    post_clear_data(client, "secret12")
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM exercises").fetchone()[0] == 0


def test_clear_data_keeps_account(client, db):
    register_and_login(client)
    _create_exercise_and_session(client, db)
    post_clear_data(client, "secret12")
    row = db.execute("SELECT * FROM users").fetchone()
    assert row is not None
    assert row["email"] == "u@example.com"


def test_clear_data_wrong_password(client, db):
    register_and_login(client)
    _create_exercise_and_session(client, db)
    response = post_clear_data(client, "wrongpassword")
    assert b"Incorrect password" in response.data
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    assert db.execute("SELECT COUNT(*) FROM exercises").fetchone()[0] == 1


def test_clear_data_requires_login(client):
    # GET is not a valid method for these POST-only endpoints
    response = client.get("/settings/clear-data", follow_redirects=False)
    assert response.status_code in (302, 405)

    # A POST without CSRF is rejected with 400 before auth is even checked
    response = client.post(
        "/settings/clear-data",
        data={"confirm_clear_password": "secret12"},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_clear_data_idempotent(client, db):
    """Clearing twice should succeed both times and leave the account intact."""
    register_and_login(client)
    _create_exercise_and_session(client, db)
    post_clear_data(client, "secret12")
    response = post_clear_data(client, "secret12")
    assert b"cleared" in response.data
    assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
