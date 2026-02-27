"""Free time slot computation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ._convert import datetime_to_nsdate, nsdate_to_datetime
from .types import EventAvailability, TimeSlot


def find_free_time(
    ek_store: Any,
    *,
    start: datetime,
    end: datetime,
    duration: timedelta,
    ek_calendars: list[Any] | None = None,
) -> list[TimeSlot]:
    """Find free time slots in the given window.

    Fetches all events in the range, merges overlapping busy intervals,
    and returns gaps that are at least as long as the requested duration.
    Events marked as "free" availability are ignored.

    Args:
        ek_store: The EKEventStore instance.
        start: Window start.
        end: Window end.
        duration: Minimum slot duration.
        ek_calendars: Optional list of EKCalendar objects to consider.
    """
    predicate = ek_store.predicateForEventsWithStartDate_endDate_calendars_(
        datetime_to_nsdate(start),
        datetime_to_nsdate(end),
        ek_calendars,
    )
    ek_events = ek_store.eventsMatchingPredicate_(predicate)

    busy_intervals: list[tuple[datetime, datetime]] = []
    for ek_event in ek_events:
        # Skip events marked as "free"
        if ek_event.availability() == EventAvailability.FREE.value:
            continue

        ev_start = nsdate_to_datetime(ek_event.startDate())
        ev_end = nsdate_to_datetime(ek_event.endDate())
        if ev_start is None or ev_end is None:
            continue

        # Clamp to window
        ev_start = (
            max(ev_start, start)
            if start.tzinfo
            else max(ev_start.replace(tzinfo=None), start)
        )
        ev_end = (
            min(ev_end, end)
            if end.tzinfo
            else min(ev_end.replace(tzinfo=None), end)
        )

        if ev_start < ev_end:
            busy_intervals.append((ev_start, ev_end))

    merged = _merge_intervals(busy_intervals)
    return _find_gaps(start, end, merged, duration)


def _merge_intervals(
    intervals: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    """Merge overlapping time intervals."""
    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged: list[tuple[datetime, datetime]] = [sorted_intervals[0]]

    for current_start, current_end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))

    return merged


def _find_gaps(
    window_start: datetime,
    window_end: datetime,
    busy: list[tuple[datetime, datetime]],
    min_duration: timedelta,
) -> list[TimeSlot]:
    """Find gaps between busy intervals that meet the minimum duration."""
    slots: list[TimeSlot] = []
    cursor = window_start

    for busy_start, busy_end in busy:
        if busy_start > cursor:
            gap = busy_start - cursor
            if gap >= min_duration:
                slots.append(TimeSlot(start=cursor, end=busy_start))
        cursor = max(cursor, busy_end)

    # Trailing gap
    if window_end > cursor:
        gap = window_end - cursor
        if gap >= min_duration:
            slots.append(TimeSlot(start=cursor, end=window_end))

    return slots
