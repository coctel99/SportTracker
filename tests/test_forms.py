"""Pure unit tests for sessions.forms — no Flask app context needed."""

import pytest

from app.tracker.sessions.forms import (
    parse_duration,
    parse_optional_int,
    parse_reps_list,
    parse_session_date,
    parse_sets_data,
)


class TestParseOptionalInt:
    def test_empty_returns_none(self):
        assert parse_optional_int("", "Sets", 1) is None

    def test_valid(self):
        assert parse_optional_int("5", "Sets", 1) == 5

    def test_at_minimum(self):
        assert parse_optional_int("0", "Reps", 0) == 0

    def test_below_minimum(self):
        with pytest.raises(ValueError, match="at least 1"):
            parse_optional_int("0", "Sets", 1)

    def test_non_integer(self):
        with pytest.raises(ValueError, match="whole number"):
            parse_optional_int("abc", "Sets", 1)


class TestParseSessionDate:
    def test_empty_returns_today(self):
        from datetime import date

        assert parse_session_date("") == date.today().isoformat()

    def test_valid(self):
        assert parse_session_date("2026-01-15") == "2026-01-15"

    def test_invalid(self):
        with pytest.raises(ValueError, match="valid date"):
            parse_session_date("2026-02-31")

    def test_strips_whitespace(self):
        assert parse_session_date("  2026-06-01  ") == "2026-06-01"


class TestParseRepsList:
    def test_valid_multiple(self):
        assert parse_reps_list("10,8,6") == [10, 8, 6]

    def test_single(self):
        assert parse_reps_list("12") == [12]

    def test_with_spaces(self):
        assert parse_reps_list(" 10 , 8 , 6 ") == [10, 8, 6]

    def test_zero_reps_allowed(self):
        assert parse_reps_list("10,0,8") == [10, 0, 8]

    def test_empty_returns_empty(self):
        # Empty string returns empty list (time-only sets are allowed)
        assert parse_reps_list("") == []

    def test_none_tokens(self):
        # Empty comma tokens → None entries
        assert parse_reps_list(",10,") == [None, 10, None]

    def test_non_integer_raises(self):
        with pytest.raises(ValueError, match="whole numbers"):
            parse_reps_list("10,abc,6")

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="negative"):
            parse_reps_list("10,-1,6")


class TestParseDuration:
    def test_empty_returns_none(self):
        assert parse_duration("", "seconds") is None

    def test_seconds(self):
        assert parse_duration("30", "seconds") == 30

    def test_minutes(self):
        assert parse_duration("2", "minutes") == 120

    def test_hours(self):
        assert parse_duration("1", "hours") == 3600

    def test_fractional_minutes(self):
        assert parse_duration("1.5", "minutes") == 90

    def test_zero_raises(self):
        with pytest.raises(ValueError, match="greater than zero"):
            parse_duration("0", "seconds")

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="greater than zero"):
            parse_duration("-5", "seconds")

    def test_invalid_unit_raises(self):
        with pytest.raises(ValueError, match="Unknown duration unit"):
            parse_duration("10", "lightyears")

    def test_non_numeric_raises(self):
        with pytest.raises(ValueError, match="number"):
            parse_duration("abc", "seconds")


class TestParseSetsData:
    def test_reps_only(self):
        assert parse_sets_data("10,8,6", "", "seconds") == [
            (10, None),
            (8, None),
            (6, None),
        ]

    def test_reps_only_with_blank_unit(self):
        """Reps-only session: comma-filled duration and blank unit must not raise."""
        assert parse_sets_data("10,8,6", ",,", "") == [(10, None), (8, None), (6, None)]

    def test_reps_only_single_set_blank_duration(self):
        """Single-set reps-only: empty duration string and blank unit must not raise."""
        assert parse_sets_data("12", "", "") == [(12, None)]

    def test_reps_only_multi_set_comma_duration(self):
        """JS always submits comma-separated duration slots even when all empty."""
        assert parse_sets_data("5,5,5", ",,,", "") == [(5, None), (5, None), (5, None)]

    def test_duration_only(self):
        assert parse_sets_data("", "60,45", "seconds") == [(None, 60), (None, 45)]

    def test_both_reps_and_duration(self):
        assert parse_sets_data("10,8", "30,45", "seconds") == [(10, 30), (8, 45)]

    def test_duration_minutes_conversion(self):
        assert parse_sets_data("", "2", "minutes") == [(None, 120)]

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            parse_sets_data("", "", "seconds")

    def test_comma_only_duration_and_blank_unit_raises(self):
        """All-blank reps AND all-blank duration (commas only) → nothing to save."""
        with pytest.raises(ValueError):
            parse_sets_data("", ",,", "")

    def test_duration_value_without_unit_raises(self):
        """A real duration value with no unit selected must raise."""
        with pytest.raises(ValueError, match="select a duration unit"):
            parse_sets_data("", "60,45", "")
