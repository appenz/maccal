"""Calendar listing and filtering."""

from __future__ import annotations

from typing import Any

from ._convert import ek_calendar_to_calendar
from .types import Calendar, CalendarType

_TYPE_NAME_MAP = {
    "local": CalendarType.LOCAL,
    "caldav": CalendarType.CALDAV,
    "exchange": CalendarType.EXCHANGE,
    "subscription": CalendarType.SUBSCRIPTION,
    "birthday": CalendarType.BIRTHDAY,
}


def list_calendars(
    ek_store: Any,
    *,
    type: str | None = None,
    source: str | None = None,
) -> list[Calendar]:
    """List calendars from the EKEventStore, with optional filters."""
    ek_calendars = ek_store.calendarsForEntityType_(0)  # EKEntityTypeEvent = 0
    result: list[Calendar] = []

    for ek_cal in ek_calendars:
        cal = ek_calendar_to_calendar(ek_cal)

        if type is not None:
            expected = _TYPE_NAME_MAP.get(type.lower())
            if expected is None:
                raise ValueError(
                    f"Unknown calendar type {type!r}. "
                    f"Valid types: {', '.join(_TYPE_NAME_MAP)}"
                )
            if cal.type != expected:
                continue

        if source is not None and (
            cal.source is None or source.lower() not in cal.source.lower()
        ):
            continue

        result.append(cal)

    return result
