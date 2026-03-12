"""Internal helpers to convert between EventKit ObjC objects and maccal dataclasses."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .types import (
    Alarm,
    Calendar,
    CalendarType,
    Event,
    EventAvailability,
    EventStatus,
    Location,
    Participant,
    ParticipantRole,
    ParticipantStatus,
    ParticipantType,
    RecurrenceEnd,
    RecurrenceFrequency,
    RecurrenceRule,
)


def nsdate_to_datetime(nsdate: Any) -> datetime | None:
    """Convert an NSDate to a timezone-aware Python datetime in the system local timezone."""
    if nsdate is None:
        return None
    timestamp = nsdate.timeIntervalSince1970()
    return datetime.fromtimestamp(timestamp).astimezone()


def datetime_to_nsdate(dt: datetime) -> Any:
    """Convert a Python datetime to an NSDate."""
    from Foundation import NSDate

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return NSDate.dateWithTimeIntervalSince1970_(dt.timestamp())


def _color_to_hex(color: Any) -> str | None:
    """Extract a hex color string from an EKCalendar color object.

    The object may be an NSColor (NSColorSpaceColor) when AppKit is loaded,
    or a raw CGColorRef in headless / no-AppKit environments.  We try the
    NSColor component accessors first, then fall back to the CoreGraphics
    C API via ctypes — avoiding NSColor.colorWithCGColor_ entirely so we
    never trigger a SIGBUS in processes without a running NSApplication.
    """
    try:
        r = int(color.redComponent() * 255)
        g = int(color.greenComponent() * 255)
        b = int(color.blueComponent() * 255)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        pass

    try:
        import ctypes
        import ctypes.util

        import objc

        _cg = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))
        _cg.CGColorGetNumberOfComponents.restype = ctypes.c_size_t
        _cg.CGColorGetNumberOfComponents.argtypes = [ctypes.c_void_p]
        _cg.CGColorGetComponents.restype = ctypes.POINTER(ctypes.c_double)
        _cg.CGColorGetComponents.argtypes = [ctypes.c_void_p]

        ptr = objc.pyobjc_id(color)
        n = _cg.CGColorGetNumberOfComponents(ptr)
        comp = _cg.CGColorGetComponents(ptr)

        if n >= 3:
            r = int(min(max(comp[0], 0.0), 1.0) * 255)
            g = int(min(max(comp[1], 0.0), 1.0) * 255)
            b = int(min(max(comp[2], 0.0), 1.0) * 255)
            return f"#{r:02x}{g:02x}{b:02x}"
        if n == 2:
            gray = int(min(max(comp[0], 0.0), 1.0) * 255)
            return f"#{gray:02x}{gray:02x}{gray:02x}"
    except Exception:
        pass

    return None


def ek_calendar_to_calendar(ek_cal: Any) -> Calendar:
    """Convert an EKCalendar to a maccal Calendar."""
    color_hex = None
    cg_color = ek_cal.color()
    if cg_color is not None:
        color_hex = _color_to_hex(cg_color)

    source_title = None
    source = ek_cal.source()
    if source is not None:
        source_title = str(source.title())

    try:
        cal_type = CalendarType(ek_cal.type())
    except ValueError:
        cal_type = CalendarType.LOCAL

    return Calendar(
        calendar_id=str(ek_cal.calendarIdentifier()),
        title=str(ek_cal.title()),
        type=cal_type,
        color=color_hex,
        source=source_title,
        is_immutable=bool(ek_cal.isImmutable()),
        allows_content_modifications=bool(ek_cal.allowsContentModifications()),
    )


def _convert_participant(ek_participant: Any) -> Participant:
    """Convert an EKParticipant to a maccal Participant."""
    email = None
    url = ek_participant.URL()
    if url is not None:
        url_str = str(url.absoluteString())
        if url_str.startswith("mailto:"):
            email = url_str[7:]

    try:
        role = ParticipantRole(ek_participant.participantRole())
    except ValueError:
        role = ParticipantRole.UNKNOWN
    try:
        status = ParticipantStatus(ek_participant.participantStatus())
    except ValueError:
        status = ParticipantStatus.UNKNOWN
    try:
        p_type = ParticipantType(ek_participant.participantType())
    except ValueError:
        p_type = ParticipantType.UNKNOWN

    return Participant(
        name=str(ek_participant.name()) if ek_participant.name() else None,
        email=email,
        role=role,
        status=status,
        type=p_type,
        is_current_user=bool(ek_participant.isCurrentUser()),
    )


def _convert_alarm(ek_alarm: Any) -> Alarm:
    """Convert an EKAlarm to a maccal Alarm."""
    abs_date = nsdate_to_datetime(ek_alarm.absoluteDate())
    relative = ek_alarm.relativeOffset()
    minutes_before = None
    if abs_date is None and relative is not None:
        minutes_before = -relative / 60.0  # EventKit uses negative seconds for "before"
    return Alarm(minutes_before=minutes_before, absolute_date=abs_date)


def _convert_recurrence_rule(ek_rule: Any) -> RecurrenceRule:
    """Convert an EKRecurrenceRule to a maccal RecurrenceRule."""
    try:
        freq = RecurrenceFrequency(ek_rule.frequency())
    except ValueError:
        freq = RecurrenceFrequency.WEEKLY

    end = None
    ek_end = ek_rule.recurrenceEnd()
    if ek_end is not None:
        end_date = nsdate_to_datetime(ek_end.endDate())
        count = ek_end.occurrenceCount() if ek_end.endDate() is None else None
        end = RecurrenceEnd(end_date=end_date, occurrence_count=count)

    days_of_week = None
    ek_days = ek_rule.daysOfTheWeek()
    if ek_days is not None:
        days_of_week = [int(d.dayOfTheWeek()) for d in ek_days]

    days_of_month = None
    ek_dom = ek_rule.daysOfTheMonth()
    if ek_dom is not None:
        days_of_month = [int(d) for d in ek_dom]

    months = None
    ek_months = ek_rule.monthsOfTheYear()
    if ek_months is not None:
        months = [int(m) for m in ek_months]

    weeks = None
    ek_weeks = ek_rule.weeksOfTheYear()
    if ek_weeks is not None:
        weeks = [int(w) for w in ek_weeks]

    days_of_year = None
    ek_doy = ek_rule.daysOfTheYear()
    if ek_doy is not None:
        days_of_year = [int(d) for d in ek_doy]

    positions = None
    ek_pos = ek_rule.setPositions()
    if ek_pos is not None:
        positions = [int(p) for p in ek_pos]

    return RecurrenceRule(
        frequency=freq,
        interval=int(ek_rule.interval()),
        days_of_week=days_of_week,
        days_of_month=days_of_month,
        months_of_year=months,
        weeks_of_year=weeks,
        days_of_year=days_of_year,
        set_positions=positions,
        end=end,
    )


def ek_event_to_event(ek_event: Any) -> Event:
    """Convert an EKEvent to a maccal Event."""
    organizer = None
    ek_org = ek_event.organizer()
    if ek_org is not None:
        organizer = _convert_participant(ek_org)

    attendees: list[Participant] = []
    ek_attendees = ek_event.attendees()
    if ek_attendees is not None:
        attendees = [_convert_participant(a) for a in ek_attendees]

    alarms: list[Alarm] = []
    ek_alarms = ek_event.alarms()
    if ek_alarms is not None:
        alarms = [_convert_alarm(a) for a in ek_alarms]

    recurrence_rules: list[RecurrenceRule] = []
    ek_rules = ek_event.recurrenceRules()
    if ek_rules is not None:
        recurrence_rules = [_convert_recurrence_rule(r) for r in ek_rules]

    location_str = ek_event.location()
    structured_loc = None
    ek_sloc = ek_event.structuredLocation()
    if ek_sloc is not None:
        geo = ek_sloc.geoLocation()
        coord = geo.coordinate() if geo else None
        structured_loc = Location(
            title=str(ek_sloc.title()) if ek_sloc.title() else None,
            latitude=coord[0] if coord else None,
            longitude=coord[1] if coord else None,
            radius=float(ek_sloc.radius()) if ek_sloc.radius() else None,
        )

    url_str = None
    ek_url = ek_event.URL()
    if ek_url is not None:
        url_str = str(ek_url.absoluteString())

    tz_name = None
    ek_tz = ek_event.timeZone()
    if ek_tz is not None:
        tz_name = str(ek_tz.name())

    try:
        availability = EventAvailability(ek_event.availability())
    except ValueError:
        availability = EventAvailability.NOT_SUPPORTED
    try:
        status = EventStatus(ek_event.status())
    except ValueError:
        status = EventStatus.NONE

    cal = ek_event.calendar()

    return Event(
        event_id=str(ek_event.eventIdentifier()),
        title=str(ek_event.title()) if ek_event.title() else "",
        start=nsdate_to_datetime(ek_event.startDate()),  # type: ignore[arg-type]
        end=nsdate_to_datetime(ek_event.endDate()),  # type: ignore[arg-type]
        is_all_day=bool(ek_event.isAllDay()),
        calendar=str(cal.title()) if cal else "",
        calendar_id=str(cal.calendarIdentifier()) if cal else "",
        location=str(location_str) if location_str else None,
        structured_location=structured_loc,
        notes=str(ek_event.notes()) if ek_event.notes() else None,
        url=url_str,
        time_zone=tz_name,
        availability=availability,
        status=status,
        organizer=organizer,
        attendees=attendees,
        alarms=alarms,
        recurrence_rules=recurrence_rules,
        creation_date=nsdate_to_datetime(ek_event.creationDate()),
        last_modified_date=nsdate_to_datetime(ek_event.lastModifiedDate()),
        is_recurring=bool(ek_event.hasRecurrenceRules()),
        is_detached=bool(ek_event.isDetached()),
        occurrence_date=nsdate_to_datetime(ek_event.occurrenceDate()),
    )
