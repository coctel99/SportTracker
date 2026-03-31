"""Dashboard DB queries."""

import calendar
from datetime import date, timedelta

from app.db import get_db


def get_dashboard_stats(
    user_id: int, year: int | None = None, month: int | None = None
) -> dict:
    """Return all stats needed to render the dashboard."""
    db = get_db()
    today = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()

    # Calendar month to display
    cal_year = year if year else today.year
    cal_month = month if month else today.month

    sessions_this_week = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM sessions
        WHERE user_id = ?
          AND session_date >= ?
        """,
        (user_id, week_start),
    ).fetchone()["count"]

    total_reps_today = db.execute(
        """
        SELECT COALESCE(SUM(es.reps), 0) AS reps
        FROM sessions s
        JOIN session_exercises se ON se.session_id = s.id
        JOIN exercise_sets es ON es.session_exercise_id = se.id
        WHERE s.user_id = ? AND s.session_date = ?
        """,
        (user_id, today.isoformat()),
    ).fetchone()["reps"]

    # Fetch all sessions in the displayed month
    month_start = date(cal_year, cal_month, 1).isoformat()
    last_day = calendar.monthrange(cal_year, cal_month)[1]
    month_end = date(cal_year, cal_month, last_day).isoformat()

    month_session_rows = db.execute(
        """
        SELECT id, session_date
        FROM sessions
        WHERE user_id = ?
          AND session_date >= ?
          AND session_date <= ?
        ORDER BY session_date ASC, id ASC
        """,
        (user_id, month_start, month_end),
    ).fetchall()

    # Map day-of-month -> list of session ids
    sessions_by_day: dict[int, list[int]] = {}
    for row in month_session_rows:
        day = int(row["session_date"].split("-")[2])
        sessions_by_day.setdefault(day, []).append(row["id"])

    # Build calendar weeks: list of weeks, each week is list of (day_number | 0)
    cal_weeks = calendar.monthcalendar(cal_year, cal_month)

    # Prev / next month navigation
    if cal_month == 1:
        prev_year, prev_month = cal_year - 1, 12
    else:
        prev_year, prev_month = cal_year, cal_month - 1

    if cal_month == 12:
        next_year, next_month = cal_year + 1, 1
    else:
        next_year, next_month = cal_year, cal_month + 1

    return {
        "sessions_this_week": sessions_this_week,
        "total_reps_today": total_reps_today,
        "cal_year": cal_year,
        "cal_month": cal_month,
        "cal_month_name": date(cal_year, cal_month, 1).strftime("%B %Y"),
        "cal_weeks": cal_weeks,
        "sessions_by_day": sessions_by_day,
        "today_day": today.day
        if (today.year == cal_year and today.month == cal_month)
        else None,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
    }
