"""CalendarStore: main entry point for accessing macOS calendars via EventKit."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta
from typing import Any

import EventKit
from Foundation import NSDate, NSRunLoop

from .types import Alarm, Calendar, Event, RecurrenceRule, TimeSlot


class CalendarAccessDeniedError(Exception):
    """Raised when the user denies calendar access."""


class CalendarStore:
    """Provides access to macOS calendars and events via EventKit.

    On initialization, requests full access to calendar events. Raises
    CalendarAccessDeniedError if the user declines the permission prompt.
    """

    SEARCHABLE_FIELDS: list[str] = [
        "title",
        "location",
        "notes",
        "url",
        "calendar",
        "organizer_name",
        "organizer_email",
        "attendee_name",
        "attendee_email",
    ]

    def __init__(self) -> None:
        self._store = EventKit.EKEventStore.alloc().init()
        self._request_access()

    def _request_access(self) -> None:
        granted_flag: list[bool] = []
        error_holder: list[Any] = []
        done = threading.Event()

        def callback(granted: bool, error: Any) -> None:
            granted_flag.append(granted)
            if error is not None:
                error_holder.append(error)
            done.set()

        self._store.requestFullAccessToEventsWithCompletion_(callback)

        while not done.is_set():
            NSRunLoop.currentRunLoop().runUntilDate_(
                NSDate.dateWithTimeIntervalSinceNow_(0.05)
            )

        if not granted_flag or not granted_flag[0]:
            msg = "Calendar access denied"
            if error_holder:
                msg += f": {error_holder[0]}"
            raise CalendarAccessDeniedError(msg)

    @property
    def ek_store(self) -> Any:
        """The underlying EKEventStore instance (for advanced usage)."""
        return self._store

    # -- Calendar operations --

    def list_calendars(
        self,
        *,
        type: str | None = None,
        source: str | None = None,
    ) -> list[Calendar]:
        """List available calendars, optionally filtered by type or source.

        Args:
            type: Filter by calendar type name (e.g. "local", "caldav", "exchange").
            source: Filter by source title (e.g. "iCloud", "Gmail").
        """
        from .calendars import list_calendars

        return list_calendars(self._store, type=type, source=source)

    # -- Event query operations --

    def get_events(
        self,
        start: datetime,
        end: datetime,
        *,
        calendars: list[str] | None = None,
    ) -> list[Event]:
        """Fetch all events in the date range.

        Recurring events are automatically expanded into individual occurrences.

        Args:
            start: Start of date range.
            end: End of date range.
            calendars: Optional list of calendar names to restrict results.
        """
        from .events import get_events

        return get_events(
            self._store,
            start=start,
            end=end,
            ek_calendars=self._resolve_calendar_names(calendars),
        )

    def find_events(
        self,
        query: str,
        *,
        start: datetime,
        end: datetime,
        calendars: list[str] | None = None,
        fields: list[str] | None = None,
        case_sensitive: bool = False,
    ) -> list[Event]:
        """Search events by text query with optional field restriction.

        Uses lazy filtering: only accesses the ObjC fields needed for matching,
        then fully converts only matching events to dataclasses.

        Args:
            query: Text to search for.
            start: Start of date range (required by EventKit).
            end: End of date range.
            calendars: Optional list of calendar names to restrict results.
            fields: Which fields to search. None means all searchable fields.
                See CalendarStore.SEARCHABLE_FIELDS for valid names.
            case_sensitive: Whether the search is case-sensitive. Default False.
        """
        from .events import find_events

        return find_events(
            self._store,
            query,
            start=start,
            end=end,
            ek_calendars=self._resolve_calendar_names(calendars),
            fields=fields,
            case_sensitive=case_sensitive,
        )

    # -- Event CRUD operations --

    def add_event(
        self,
        *,
        title: str,
        start: datetime,
        end: datetime,
        calendar: str | None = None,
        location: str | None = None,
        notes: str | None = None,
        url: str | None = None,
        is_all_day: bool = False,
        availability: int | None = None,
        alarms: list[Alarm] | None = None,
        recurrence: RecurrenceRule | None = None,
    ) -> Event:
        """Create a new calendar event.

        Args:
            title: Event title (required).
            start: Event start time (required).
            end: Event end time (required).
            calendar: Name of target calendar. Uses system default if None.
            location: Location string.
            notes: Event notes/description.
            url: URL associated with the event.
            is_all_day: Whether this is an all-day event.
            availability: EventKit availability (0=busy, 1=free, 2=tentative, 3=unavailable).
            alarms: List of Alarm objects.
            recurrence: A RecurrenceRule for recurring events.
        """
        from .events import add_event

        return add_event(
            self._store,
            title=title,
            start=start,
            end=end,
            calendar_name=calendar,
            location=location,
            notes=notes,
            url=url,
            is_all_day=is_all_day,
            availability=availability,
            alarms=alarms,
            recurrence=recurrence,
        )

    def update_event(
        self,
        event_id: str,
        *,
        title: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        location: str | None = ...,  # type: ignore[assignment]
        notes: str | None = ...,  # type: ignore[assignment]
        url: str | None = ...,  # type: ignore[assignment]
        is_all_day: bool | None = None,
        span: str = "this",
        occurrence_date: datetime | None = None,
    ) -> Event:
        """Update an existing calendar event.

        For recurring events, you must specify span and occurrence_date.
        Omitting occurrence_date on a recurring event raises ValueError.

        Args:
            event_id: The event identifier.
            title: New title (or None to leave unchanged).
            start: New start time.
            end: New end time.
            location: New location (None to clear, omit to leave unchanged).
            notes: New notes (None to clear, omit to leave unchanged).
            url: New URL (None to clear, omit to leave unchanged).
            is_all_day: New all-day flag.
            span: For recurring events: "this" or "future".
            occurrence_date: Which occurrence to modify (required for recurring).
        """
        from .events import update_event

        return update_event(
            self._store,
            event_id,
            title=title,
            start=start,
            end=end,
            location=location,
            notes=notes,
            url=url,
            is_all_day=is_all_day,
            span=span,
            occurrence_date=occurrence_date,
        )

    def delete_event(
        self,
        event_id: str,
        *,
        span: str = "this",
        occurrence_date: datetime | None = None,
    ) -> None:
        """Delete a calendar event.

        For recurring events, you must specify span and occurrence_date.
        Omitting occurrence_date on a recurring event raises ValueError.

        Args:
            event_id: The event identifier.
            span: For recurring events: "this" or "future".
            occurrence_date: Which occurrence to delete (required for recurring).
        """
        from .events import delete_event

        delete_event(
            self._store,
            event_id,
            span=span,
            occurrence_date=occurrence_date,
        )

    # -- Availability --

    def find_free_time(
        self,
        start: datetime,
        end: datetime,
        duration: timedelta,
        *,
        calendars: list[str] | None = None,
    ) -> list[TimeSlot]:
        """Find free time slots in the given window.

        Fetches events, merges busy intervals (ignoring events marked "free"),
        and returns gaps at least as long as the requested duration.

        Args:
            start: Window start.
            end: Window end.
            duration: Minimum slot duration.
            calendars: Optional list of calendar names to consider.
        """
        from .availability import find_free_time

        return find_free_time(
            self._store,
            start=start,
            end=end,
            duration=duration,
            ek_calendars=self._resolve_calendar_names(calendars),
        )

    # -- Internal helpers --

    def _resolve_calendar_names(
        self, names: list[str] | None
    ) -> list[Any] | None:
        """Resolve calendar title strings to EKCalendar objects."""
        if names is None:
            return None
        all_cals = self._store.calendarsForEntityType_(0)  # EKEntityTypeEvent = 0
        name_set = {n.lower() for n in names}
        return [c for c in all_cals if str(c.title()).lower() in name_set]
