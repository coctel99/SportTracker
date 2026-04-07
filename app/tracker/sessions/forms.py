"""Form-input parsing for session creation.

All functions raise ``ValueError`` with a user-facing message on bad input.
They are intentionally free of Flask/DB dependencies so they can be unit-tested
without an application context.
"""

from datetime import date

DURATION_UNIT_MULTIPLIERS = {
    "seconds": 1,
    "minutes": 60,
    "hours": 3600,
}


def parse_optional_int(value: str, field_name: str, minimum: int) -> int | None:
    """Parse an optional integer form field.

    Returns ``None`` if *value* is empty.  Raises ``ValueError`` if the value
    is not a whole number or is below *minimum*.
    """
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a whole number.") from exc
    if parsed < minimum:
        raise ValueError(f"{field_name} must be at least {minimum}.")
    return parsed


def parse_session_date(value: str) -> str:
    """Return an ISO-format date string.

    Defaults to today when *value* is blank.  Raises ``ValueError`` for an
    unparseable date string.
    """
    raw = value.strip() if value else ""
    if not raw:
        return date.today().isoformat()
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise ValueError("Session date must be a valid date.") from exc


def parse_reps_list(value: str) -> list[int | None]:
    """Parse a comma-separated reps string into a list of non-negative ints or Nones.

    Raises ``ValueError`` if non-empty tokens contain non-integers or negative numbers.
    """
    if not value or not value.strip():
        return []
    result = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            result.append(None)
            continue
        try:
            reps = int(token)
        except ValueError as exc:
            raise ValueError("Reps must be comma-separated whole numbers.") from exc
        if reps < 0:
            raise ValueError("Reps cannot be negative.")
        result.append(reps)
    return result


def parse_duration(value: str, unit: str) -> int | None:
    """Parse a duration value + unit into total seconds.

    Returns ``None`` if *value* is blank.
    Raises ``ValueError`` for invalid values.
    ``unit`` must be one of: ``"seconds"``, ``"minutes"``, ``"hours"``.
    """
    if not value or not value.strip():
        return None
    unit = unit.strip().lower() if unit else "seconds"
    multiplier = DURATION_UNIT_MULTIPLIERS.get(unit)
    if multiplier is None:
        raise ValueError(
            f"Unknown duration unit '{unit}'. Use seconds, minutes, or hours."
        )
    try:
        amount = float(value.strip())
    except ValueError as exc:
        raise ValueError("Duration must be a number.") from exc
    if amount <= 0:
        raise ValueError("Duration must be greater than zero.")
    seconds = int(round(amount * multiplier))
    if seconds <= 0:
        raise ValueError("Duration must be greater than zero.")
    return seconds


def parse_duration_list(value: str, unit: str) -> list[int | None]:
    """Parse a comma-separated duration string into a list of second values or Nones.

    Returns a list of the same length as the comma-separated tokens.
    Empty tokens produce ``None``.
    """
    result = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            result.append(None)
        else:
            result.append(parse_duration(token, unit))
    return result


def _has_any_value(raw: str) -> bool:
    """Return True if *raw* contains at least one non-blank comma-separated token."""
    return any(token.strip() for token in raw.split(","))


def parse_sets_data(
    reps_raw: str,
    duration_raw: str,
    duration_unit: str,
) -> list[tuple[int | None, int | None]]:
    """Combine reps and duration lists into per-set tuples ``(reps, duration_seconds)``.

    At least one of reps or duration must be provided per set.
    Raises ``ValueError`` if no data is provided for any set, if both lists are
    entirely empty, or if a duration value is present but the unit is not selected.
    """
    reps_list = parse_reps_list(reps_raw) if _has_any_value(reps_raw) else []

    if _has_any_value(duration_raw):
        if not duration_unit or duration_unit.strip() not in DURATION_UNIT_MULTIPLIERS:
            raise ValueError(
                "Please select a duration unit (seconds, minutes, or hours)."
            )
        dur_list = parse_duration_list(duration_raw, duration_unit)
    else:
        dur_list = []

    # Determine the number of sets from whichever list is longer
    count = max(len(reps_list), len(dur_list))
    if count == 0:
        raise ValueError(
            "At least reps or duration must be entered for each exercise row."
        )

    result = []
    for i in range(count):
        reps = reps_list[i] if i < len(reps_list) else None
        dur = dur_list[i] if i < len(dur_list) else None
        if reps is None and dur is None:
            raise ValueError("Each set must have at least reps or a duration.")
        result.append((reps, dur))
    return result
