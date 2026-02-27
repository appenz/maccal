"""maccal: Python library to access macOS calendars via EventKit."""

from .store import CalendarAccessDeniedError, CalendarStore
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
    TimeSlot,
)

__all__ = [
    "Alarm",
    "Calendar",
    "CalendarAccessDeniedError",
    "CalendarStore",
    "CalendarType",
    "Event",
    "EventAvailability",
    "EventStatus",
    "Location",
    "Participant",
    "ParticipantRole",
    "ParticipantStatus",
    "ParticipantType",
    "RecurrenceEnd",
    "RecurrenceFrequency",
    "RecurrenceRule",
    "TimeSlot",
]
