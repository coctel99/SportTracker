"""Tests for multi-session day behaviour."""

from tests.conftest import get_csrf_token, register


def _setup(client, db):
    """Register, login, create two exercises, return (ex1_id, ex2_id)."""
    register(client)
    client.post(
        "/exercises",
        data={"name": "Squat", "csrf_token": get_csrf_token(client, "/exercises")},
        follow_redirects=True,
    )
    client.post(
        "/exercises",
        data={"name": "Press", "csrf_token": get_csrf_token(client, "/exercises")},
        follow_redirects=True,
    )
    ex1 = db.execute("SELECT id FROM exercises WHERE name = 'Squat'").fetchone()["id"]
    ex2 = db.execute("SELECT id FROM exercises WHERE name = 'Press'").fetchone()["id"]
    return ex1, ex2


def _log_session(client, date, exercise_id, reps):
    client.post(
        "/sessions/new",
        data={
            "session_date": date,
            "exercise_id[]": [str(exercise_id)],
            "reps[]": [reps],
            "csrf_token": get_csrf_token(client, "/sessions/new"),
        },
        follow_redirects=True,
    )


def test_training_day_single_session_shows_page(client, db):
    """With one session on the day, /training-day/<date> renders the training_day page."""
    ex1, _ = _setup(client, db)
    _log_session(client, "2026-03-31", ex1, "5,5,5")
    session_id = db.execute("SELECT id FROM sessions").fetchone()["id"]

    response = client.get("/training-day/2026-03-31")

    assert response.status_code == 200
    assert f"/sessions/{session_id}".encode() in response.data


def test_training_day_no_session_redirects_to_new(client, db):
    """With no sessions on the day, /training-day/<date> redirects to new_session."""
    register(client)

    response = client.get("/training-day/2026-03-31")

    assert response.status_code == 302
    assert "/sessions/new" in response.headers["Location"]
    assert "2026-03-31" in response.headers["Location"]


def test_training_day_multiple_sessions_shows_page(client, db):
    """With two sessions, the training-day page is rendered (not redirected)."""
    ex1, ex2 = _setup(client, db)
    _log_session(client, "2026-03-31", ex1, "10,8")
    _log_session(client, "2026-03-31", ex2, "12,10,8")

    response = client.get("/training-day/2026-03-31")

    assert response.status_code == 200
    assert b"2026-03-31" in response.data
    assert b"Session 1" in response.data
    assert b"Session 2" in response.data
    assert b"Squat" in response.data
    assert b"Press" in response.data


def test_training_day_shows_correct_rep_totals(client, db):
    """Each session card shows the correct total reps for its exercises."""
    ex1, ex2 = _setup(client, db)
    _log_session(client, "2026-03-31", ex1, "10,8")  # 18 reps
    _log_session(client, "2026-03-31", ex2, "12,10,8")  # 30 reps

    response = client.get("/training-day/2026-03-31")

    assert b"18" in response.data
    assert b"30" in response.data


def test_training_day_requires_login(client, db):
    response = client.get("/training-day/2026-03-31")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_dashboard_total_reps_sums_all_sessions_today(client, db, app):
    """total_reps_today must aggregate across ALL sessions on the same day."""
    from datetime import date

    ex1, ex2 = _setup(client, db)
    today = date.today().isoformat()

    _log_session(client, today, ex1, "10,10")  # 20 reps
    _log_session(client, today, ex2, "5,5,5")  # 15 reps  → total 35

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"35" in response.data


def test_dashboard_sessions_this_week_counts_all_sessions(client, db):
    """sessions_this_week must count each session row, not each day."""
    from datetime import date, timedelta

    ex1, ex2 = _setup(client, db)
    today = date.today()
    # Use Monday of the current week to stay within the week
    monday = (today - timedelta(days=today.weekday())).isoformat()

    _log_session(client, monday, ex1, "5,5")
    _log_session(client, monday, ex2, "5,5")  # second session same day

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"2" in response.data  # 2 sessions this week


def test_dashboard_calendar_shows_badge_for_multiple_sessions(client, db):
    """The amber badge with count appears on days with more than one session."""
    ex1, ex2 = _setup(client, db)
    _log_session(client, "2026-03-31", ex1, "5,5")
    _log_session(client, "2026-03-31", ex2, "5,5")

    response = client.get("/dashboard?year=2026&month=3")

    assert response.status_code == 200
    # The badge showing "2" and the training-day link should both be present
    assert b"/training-day/2026-03-31" in response.data
    assert b"2 sessions" in response.data


def test_reps_only_session_with_browser_duration_payload(client, db):
    """Regression: the browser always submits comma-filled duration[] slots and a
    blank duration_unit[]. A reps-only session must save successfully without
    raising 'Please select a duration unit'."""
    ex1, _ = _setup(client, db)
    csrf = get_csrf_token(client, "/sessions/new")

    # Mimic exactly what the JS submit handler sends for 3 sets, no duration entered:
    #   reps[]        = "5,5,5"
    #   duration[]    = ",,"      (three blank slots joined by commas)
    #   duration_unit[]= ""       (blank — "unit" option selected)
    response = client.post(
        "/sessions/new",
        data={
            "session_date": "2026-04-07",
            "exercise_id[]": [str(ex1)],
            "reps[]": ["5,5,5"],
            "duration[]": [",,"],
            "duration_unit[]": [""],
            "csrf_token": csrf,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"An error occurred" not in response.data
    assert b"duration unit" not in response.data
    assert db.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"] == 1
