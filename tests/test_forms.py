"""Pure unit tests for sessions.forms — no Flask app context needed."""

import pytest

from app.tracker.sessions.forms import (
    parse_optional_int,
    parse_reps_list,
    parse_session_date,
)

# ── parse_optional_int ────────────────────────────────────────────────────────


def test_parse_optional_int_empty_returns_none():
    assert parse_optional_int("", "Sets", 1) is None


def test_parse_optional_int_valid():
    assert parse_optional_int("5", "Sets", 1) == 5


def test_parse_optional_int_at_minimum():
    assert parse_optional_int("0", "Reps", 0) == 0


def test_parse_optional_int_below_minimum():
    with pytest.raises(ValueError, match="at least 1"):
        parse_optional_int("0", "Sets", 1)


def test_parse_optional_int_non_integer():
    with pytest.raises(ValueError, match="whole number"):
        parse_optional_int("abc", "Sets", 1)


# ── parse_session_date ────────────────────────────────────────────────────────


def test_parse_session_date_empty_returns_today():
    from datetime import date

    assert parse_session_date("") == date.today().isoformat()


def test_parse_session_date_valid():
    assert parse_session_date("2026-01-15") == "2026-01-15"


def test_parse_session_date_invalid():
    with pytest.raises(ValueError, match="valid date"):
        parse_session_date("2026-02-31")


def test_parse_session_date_strips_whitespace():
    assert parse_session_date("  2026-06-01  ") == "2026-06-01"


# ── parse_reps_list ───────────────────────────────────────────────────────────


def test_parse_reps_list_valid():
    assert parse_reps_list("10,8,6") == [10, 8, 6]


def test_parse_reps_list_single():
    assert parse_reps_list("12") == [12]


def test_parse_reps_list_with_spaces():
    assert parse_reps_list(" 10 , 8 , 6 ") == [10, 8, 6]


def test_parse_reps_list_zero_reps_allowed():
    assert parse_reps_list("10,0,8") == [10, 0, 8]


def test_parse_reps_list_empty_raises():
    with pytest.raises(ValueError, match="required"):
        parse_reps_list("")


def test_parse_reps_list_non_integer_raises():
    with pytest.raises(ValueError, match="whole numbers"):
        parse_reps_list("10,abc,6")


def test_parse_reps_list_negative_raises():
    with pytest.raises(ValueError, match="negative"):
        parse_reps_list("10,-1,6")
