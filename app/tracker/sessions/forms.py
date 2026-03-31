"""Form-input parsing for session creation.

All functions raise ``ValueError`` with a user-facing message on bad input.
They are intentionally free of Flask/DB dependencies so they can be unit-tested
without an application context.
"""

from datetime import date


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


def parse_reps_list(value: str) -> list[int]:
    """Parse a comma-separated reps string into a list of non-negative ints.

    Raises ``ValueError`` if the string is empty, contains non-integers, or
    contains negative numbers.
    """
    result = []
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            reps = int(token)
        except ValueError as exc:
            raise ValueError("Reps must be comma-separated whole numbers.") from exc
        if reps < 0:
            raise ValueError("Reps cannot be negative.")
        result.append(reps)

    if not result:
        raise ValueError("Reps are required for each exercise row.")
    return result
