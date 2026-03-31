"""Tests for the profile page, editing personal details, and changing password."""

from tests.conftest import get_csrf_token, login, register


def register_and_login(client):
    """Register (which auto-logs in) and return the client ready to use."""
    register(client)
    return client


def post_edit(client, **fields):
    csrf = get_csrf_token(client, "/profile")
    return client.post(
        "/profile/edit",
        data={"csrf_token": csrf, **fields},
        follow_redirects=True,
    )


def post_change_password(client, current, new, confirm):
    csrf = get_csrf_token(client, "/profile")
    return client.post(
        "/profile/change-password",
        data={
            "csrf_token": csrf,
            "current_password": current,
            "new_password": new,
            "confirm_password": confirm,
        },
        follow_redirects=True,
    )


def test_profile_page_loads(client):
    register_and_login(client)
    response = client.get("/profile")
    assert response.status_code == 200
    assert b"Personal details" in response.data


def test_profile_shows_user_name(client):
    register(client, name="Alice Smith")
    response = client.get("/profile")
    assert b"Alice Smith" in response.data


def test_profile_shows_user_email(client):
    register(client, email="alice@example.com")
    response = client.get("/profile")
    assert b"alice@example.com" in response.data


def test_profile_requires_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


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
    # Now clear them
    post_edit(client, name="Test User", date_of_birth="", weight="")

    row = db.execute("SELECT date_of_birth, weight FROM users").fetchone()
    assert row["date_of_birth"] is None
    assert row["weight"] is None


def test_edit_profile_shows_success_flash(client):
    register_and_login(client)

    response = post_edit(client, name="New Name", date_of_birth="", weight="")

    assert b"Profile updated" in response.data


def test_edit_profile_rejects_empty_name(client, db):
    register_and_login(client)

    response = post_edit(client, name="", date_of_birth="", weight="")

    assert b"Name is required" in response.data
    row = db.execute("SELECT name FROM users").fetchone()
    assert row["name"] == "Test User"  # unchanged


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


def test_change_password_success(client):
    register_and_login(client)

    response = post_change_password(client, "secret12", "newpass99", "newpass99")

    assert b"Password changed successfully" in response.data


def test_change_password_allows_login_with_new_password(client):
    register_and_login(client)
    post_change_password(client, "secret12", "newpass99", "newpass99")

    # Log out then log in with new password
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
    """On wrong current password the page re-renders with the password block open."""
    register_and_login(client)

    response = post_change_password(client, "wrongpass", "newpass99", "newpass99")

    # The password edit form should be visible (not hidden)
    assert b"current_password" in response.data
    assert b"incorrect" in response.data


def test_old_password_rejected_after_change(client):
    """After a successful change the old password no longer works."""
    register_and_login(client)
    post_change_password(client, "secret12", "newpass99", "newpass99")

    csrf = get_csrf_token(client, "/dashboard")
    client.post("/logout", data={"csrf_token": csrf})
    response = login(client, password="secret12")

    assert b"Invalid credentials" in response.data
