"""Tests for maccal data types."""

from datetime import UTC, datetime, timedelta

from maccal.types import (
    Alarm,
    Calendar,
    CalendarType,
    Event,
    EventAvailability,
    EventStatus,
    Location,
    Participant,
    ParticipantRole,
    RecurrenceEnd,
    RecurrenceFrequency,
    RecurrenceRule,
    TimeSlot,
)


def test_timeslot_duration():
    slot = TimeSlot(
        start=datetime(2026, 3, 15, 9, 0, tzinfo=UTC),
        end=datetime(2026, 3, 15, 10, 30, tzinfo=UTC),
    )
    assert slot.duration == timedelta(hours=1, minutes=30)


def test_event_defaults():
    event = Event(
        event_id="abc123",
        title="Test",
        start=datetime(2026, 3, 15, 9, 0, tzinfo=UTC),
        end=datetime(2026, 3, 15, 10, 0, tzinfo=UTC),
        is_all_day=False,
        calendar="Work",
        calendar_id="cal-1",
    )
    assert event.location is None
    assert event.attendees == []
    assert event.alarms == []
    assert event.recurrence_rules == []
    assert event.is_recurring is False
    assert event.availability == EventAvailability.NOT_SUPPORTED
    assert event.status == EventStatus.NONE


def test_calendar_frozen():
    cal = Calendar(
        calendar_id="cal-1",
        title="Work",
        type=CalendarType.LOCAL,
    )
    assert cal.title == "Work"
    assert cal.is_immutable is False


def test_alarm_minutes_before():
    alarm = Alarm(minutes_before=15)
    assert alarm.minutes_before == 15
    assert alarm.absolute_date is None


def test_alarm_absolute_date():
    dt = datetime(2026, 3, 15, 8, 45, tzinfo=UTC)
    alarm = Alarm(absolute_date=dt)
    assert alarm.absolute_date == dt
    assert alarm.minutes_before is None


def test_recurrence_rule_defaults():
    rule = RecurrenceRule()
    assert rule.frequency == RecurrenceFrequency.WEEKLY
    assert rule.interval == 1
    assert rule.days_of_week is None
    assert rule.end is None


def test_recurrence_with_end():
    rule = RecurrenceRule(
        frequency=RecurrenceFrequency.DAILY,
        end=RecurrenceEnd(occurrence_count=10),
    )
    assert rule.end.occurrence_count == 10
    assert rule.end.end_date is None


def test_location():
    loc = Location(title="Apple Park", latitude=37.3349, longitude=-122.0090, radius=100.0)
    assert loc.title == "Apple Park"
    assert loc.latitude == 37.3349


def test_participant():
    p = Participant(
        name="Alice",
        email="alice@example.com",
        role=ParticipantRole.REQUIRED,
    )
    assert p.name == "Alice"
    assert p.is_current_user is False
