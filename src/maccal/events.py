"""Event query, search, and CRUD operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import EventKit

from ._convert import datetime_to_nsdate, ek_event_to_event
from .types import Alarm, Event, RecurrenceRule

# Mapping from SEARCHABLE_FIELDS names to extraction functions.
# Each function takes an EKEvent (ObjC) and returns an iterable of strings to search.
_FIELD_EXTRACTORS: dict[str, Any] = {
    "title": lambda e: [str(e.title())] if e.title() else [],
    "location": lambda e: [str(e.location())] if e.location() else [],
    "notes": lambda e: [str(e.notes())] if e.notes() else [],
    "url": lambda e: (
        [str(e.URL().absoluteString())] if e.URL() else []
    ),
    "calendar": lambda e: (
        [str(e.calendar().title())] if e.calendar() and e.calendar().title() else []
    ),
    "organizer_name": lambda e: (
        [str(e.organizer().name())] if e.organizer() and e.organizer().name() else []
    ),
    "organizer_email": lambda e: _participant_email(e.organizer()),
    "attendee_name": lambda e: (
        [str(a.name()) for a in (e.attendees() or []) if a.name()]
    ),
    "attendee_email": lambda e: _attendee_emails(e),
}


def _participant_email(participant: Any) -> list[str]:
    if participant is None:
        return []
    url = participant.URL()
    if url is None:
        return []
    url_str = str(url.absoluteString())
    if url_str.startswith("mailto:"):
        return [url_str[7:]]
    return []


def _attendee_emails(ek_event: Any) -> list[str]:
    attendees = ek_event.attendees()
    if attendees is None:
        return []
    result = []
    for a in attendees:
        url = a.URL()
        if url is not None:
            url_str = str(url.absoluteString())
            if url_str.startswith("mailto:"):
                result.append(url_str[7:])
    return result


def _ek_event_matches(
    ek_event: Any,
    query_lower: str,
    field_names: list[str],
) -> bool:
    """Check if an EKEvent matches the query in any of the specified fields.

    Operates on the raw ObjC object to minimize bridge calls (lazy filtering).
    """
    for field_name in field_names:
        extractor = _FIELD_EXTRACTORS.get(field_name)
        if extractor is None:
            continue
        for value in extractor(ek_event):
            if query_lower in value.lower():
                return True
    return False


def get_events(
    ek_store: Any,
    *,
    start: datetime,
    end: datetime,
    ek_calendars: list[Any] | None = None,
) -> list[Event]:
    """Fetch all events in the date range, with optional calendar filter."""
    predicate = ek_store.predicateForEventsWithStartDate_endDate_calendars_(
        datetime_to_nsdate(start),
        datetime_to_nsdate(end),
        ek_calendars,
    )
    ek_events = ek_store.eventsMatchingPredicate_(predicate)
    return [ek_event_to_event(e) for e in ek_events]


def find_events(
    ek_store: Any,
    query: str,
    *,
    start: datetime,
    end: datetime,
    ek_calendars: list[Any] | None = None,
    fields: list[str] | None = None,
    case_sensitive: bool = False,
) -> list[Event]:
    """Search events by text query with optional field restriction.

    Uses lazy filtering: only accesses the fields needed for matching on each
    ObjC event object, and only converts matching events to full dataclasses.

    Args:
        query: Text to search for.
        start: Start of date range (required by EventKit).
        end: End of date range.
        ek_calendars: Optional list of EKCalendar objects to restrict search.
        fields: Which fields to search. None means all searchable fields.
            Valid names: title, location, notes, url, calendar,
            organizer_name, organizer_email, attendee_name, attendee_email.
        case_sensitive: Whether the search is case-sensitive. Default False.
    """
    if fields is not None:
        invalid = set(fields) - set(_FIELD_EXTRACTORS)
        if invalid:
            raise ValueError(
                f"Unknown search fields: {invalid}. "
                f"Valid fields: {sorted(_FIELD_EXTRACTORS)}"
            )
        search_fields = fields
    else:
        search_fields = list(_FIELD_EXTRACTORS)

    predicate = ek_store.predicateForEventsWithStartDate_endDate_calendars_(
        datetime_to_nsdate(start),
        datetime_to_nsdate(end),
        ek_calendars,
    )
    ek_events = ek_store.eventsMatchingPredicate_(predicate)

    query_normalized = query if case_sensitive else query.lower()
    matches = []
    for ek_event in ek_events:
        if _ek_event_matches(ek_event, query_normalized, search_fields):
            matches.append(ek_event_to_event(ek_event))
    return matches


def add_event(
    ek_store: Any,
    *,
    title: str,
    start: datetime,
    end: datetime,
    calendar_name: str | None = None,
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
        calendar_name: Name of target calendar. Uses default if None.
        location: Location string.
        notes: Event notes/description.
        url: URL associated with the event.
        is_all_day: Whether this is an all-day event.
        availability: EventKit availability constant (0=busy, 1=free, etc.).
        alarms: List of Alarm objects.
        recurrence: A RecurrenceRule for recurring events.
    """
    from Foundation import NSURL

    ek_event = EventKit.EKEvent.eventWithEventStore_(ek_store)
    ek_event.setTitle_(title)
    ek_event.setStartDate_(datetime_to_nsdate(start))
    ek_event.setEndDate_(datetime_to_nsdate(end))
    ek_event.setAllDay_(is_all_day)

    if calendar_name is not None:
        calendars = ek_store.calendarsForEntityType_(0)
        target = None
        for cal in calendars:
            if str(cal.title()).lower() == calendar_name.lower():
                target = cal
                break
        if target is None:
            raise ValueError(f"Calendar {calendar_name!r} not found")
        ek_event.setCalendar_(target)
    else:
        ek_event.setCalendar_(ek_store.defaultCalendarForNewEvents())

    if location is not None:
        ek_event.setLocation_(location)
    if notes is not None:
        ek_event.setNotes_(notes)
    if url is not None:
        ek_event.setURL_(NSURL.URLWithString_(url))
    if availability is not None:
        ek_event.setAvailability_(availability)

    if alarms:
        for alarm in alarms:
            if alarm.minutes_before is not None:
                ek_alarm = EventKit.EKAlarm.alarmWithRelativeOffset_(
                    -alarm.minutes_before * 60
                )
            elif alarm.absolute_date is not None:
                ek_alarm = EventKit.EKAlarm.alarmWithAbsoluteDate_(
                    datetime_to_nsdate(alarm.absolute_date)
                )
            else:
                continue
            ek_event.addAlarm_(ek_alarm)

    if recurrence is not None:
        ek_rule = _build_recurrence_rule(recurrence)
        ek_event.addRecurrenceRule_(ek_rule)

    error = ek_store.saveEvent_span_error_(
        ek_event, EventKit.EKSpanThisEvent, None
    )
    if error is not None and error[1] is not None:
        raise RuntimeError(f"Failed to save event: {error[1]}")

    return ek_event_to_event(ek_event)


def update_event(
    ek_store: Any,
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

    For recurring events, span and occurrence_date are required.

    Args:
        event_id: The event identifier.
        title: New title (or None to leave unchanged).
        start: New start time.
        end: New end time.
        location: New location (pass None to clear, omit to leave unchanged).
        notes: New notes (pass None to clear, omit to leave unchanged).
        url: New URL (pass None to clear, omit to leave unchanged).
        is_all_day: New all-day flag.
        span: For recurring events: "this" or "future".
        occurrence_date: Which occurrence to modify (required for recurring).
    """
    ek_event = ek_store.eventWithIdentifier_(event_id)
    if ek_event is None:
        raise ValueError(f"Event {event_id!r} not found")

    if ek_event.hasRecurrenceRules() and occurrence_date is None:
        raise ValueError(
            "This is a recurring event. You must specify occurrence_date and span "
            '("this" or "future") to indicate which occurrences to modify.'
        )

    ek_span = _resolve_span(span)

    if title is not None:
        ek_event.setTitle_(title)
    if start is not None:
        ek_event.setStartDate_(datetime_to_nsdate(start))
    if end is not None:
        ek_event.setEndDate_(datetime_to_nsdate(end))
    if is_all_day is not None:
        ek_event.setAllDay_(is_all_day)
    if location is not ...:
        ek_event.setLocation_(location)
    if notes is not ...:
        ek_event.setNotes_(notes)
    if url is not ...:
        from Foundation import NSURL

        ek_event.setURL_(NSURL.URLWithString_(url) if url else None)

    error = ek_store.saveEvent_span_error_(ek_event, ek_span, None)
    if error is not None and error[1] is not None:
        raise RuntimeError(f"Failed to update event: {error[1]}")

    return ek_event_to_event(ek_event)


def delete_event(
    ek_store: Any,
    event_id: str,
    *,
    span: str = "this",
    occurrence_date: datetime | None = None,
) -> None:
    """Delete a calendar event.

    For recurring events, span and occurrence_date are required.

    Args:
        event_id: The event identifier.
        span: For recurring events: "this" or "future".
        occurrence_date: Which occurrence to delete (required for recurring).
    """
    ek_event = ek_store.eventWithIdentifier_(event_id)
    if ek_event is None:
        raise ValueError(f"Event {event_id!r} not found")

    if ek_event.hasRecurrenceRules() and occurrence_date is None:
        raise ValueError(
            "This is a recurring event. You must specify occurrence_date and span "
            '("this" or "future") to indicate which occurrences to delete.'
        )

    ek_span = _resolve_span(span)
    error = ek_store.removeEvent_span_error_(ek_event, ek_span, None)
    if error is not None and error[1] is not None:
        raise RuntimeError(f"Failed to delete event: {error[1]}")


def _resolve_span(span: str) -> int:
    if span == "this":
        return EventKit.EKSpanThisEvent
    elif span == "future":
        return EventKit.EKSpanFutureEvents
    else:
        raise ValueError(f"span must be 'this' or 'future', got {span!r}")


def _build_recurrence_rule(rule: RecurrenceRule) -> Any:
    """Build an EKRecurrenceRule from a maccal RecurrenceRule."""
    ek_end = None
    if rule.end is not None:
        if rule.end.end_date is not None:
            ek_end = EventKit.EKRecurrenceEnd.recurrenceEndWithEndDate_(
                datetime_to_nsdate(rule.end.end_date)
            )
        elif rule.end.occurrence_count is not None:
            ek_end = EventKit.EKRecurrenceEnd.recurrenceEndWithOccurrenceCount_(
                rule.end.occurrence_count
            )

    days_of_week = None
    if rule.days_of_week is not None:
        days_of_week = [
            EventKit.EKRecurrenceDayOfWeek.dayOfWeek_(d) for d in rule.days_of_week
        ]

    from Foundation import NSArray

    days_of_month = None
    if rule.days_of_month is not None:
        days_of_month = NSArray.arrayWithArray_(rule.days_of_month)

    months = None
    if rule.months_of_year is not None:
        months = NSArray.arrayWithArray_(rule.months_of_year)

    return (
        EventKit.EKRecurrenceRule.alloc()
        .initRecurrenceWithFrequency_interval_daysOfTheWeek_daysOfTheMonth_monthsOfTheYear_weeksOfTheYear_daysOfTheYear_setPositions_end_(
            rule.frequency.value,
            rule.interval,
            days_of_week,
            days_of_month,
            months,
            NSArray.arrayWithArray_(rule.weeks_of_year)
            if rule.weeks_of_year
            else None,
            NSArray.arrayWithArray_(rule.days_of_year)
            if rule.days_of_year
            else None,
            NSArray.arrayWithArray_(rule.set_positions)
            if rule.set_positions
            else None,
            ek_end,
        )
    )
