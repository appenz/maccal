"""Data types for maccal: dataclass representations of EventKit objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class EventAvailability(Enum):
    NOT_SUPPORTED = -1
    BUSY = 0
    FREE = 1
    TENTATIVE = 2
    UNAVAILABLE = 3


class EventStatus(Enum):
    NONE = 0
    CONFIRMED = 1
    TENTATIVE = 2
    CANCELED = 3


class ParticipantRole(Enum):
    UNKNOWN = 0
    REQUIRED = 1
    OPTIONAL = 2
    CHAIR = 3
    NON_PARTICIPANT = 4


class ParticipantStatus(Enum):
    UNKNOWN = 0
    PENDING = 1
    ACCEPTED = 2
    DECLINED = 3
    TENTATIVE = 4
    DELEGATED = 5
    COMPLETED = 6
    IN_PROCESS = 7


class ParticipantType(Enum):
    UNKNOWN = 0
    PERSON = 1
    ROOM = 2
    RESOURCE = 3
    GROUP = 4


class CalendarType(Enum):
    LOCAL = 0
    CALDAV = 1
    EXCHANGE = 2
    SUBSCRIPTION = 3
    BIRTHDAY = 4


class RecurrenceFrequency(Enum):
    DAILY = 0
    WEEKLY = 1
    MONTHLY = 2
    YEARLY = 3


@dataclass(frozen=True)
class Location:
    """Structured location with optional geo coordinates."""

    title: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius: float | None = None


@dataclass(frozen=True)
class Participant:
    """A person associated with a calendar event."""

    name: str | None = None
    email: str | None = None
    role: ParticipantRole = ParticipantRole.UNKNOWN
    status: ParticipantStatus = ParticipantStatus.UNKNOWN
    type: ParticipantType = ParticipantType.UNKNOWN
    is_current_user: bool = False


@dataclass(frozen=True)
class Alarm:
    """An alarm/reminder for a calendar event.

    Specify either minutes_before (relative) or absolute_date, not both.
    """

    minutes_before: float | None = None
    absolute_date: datetime | None = None


@dataclass(frozen=True)
class RecurrenceEnd:
    """When a recurrence rule stops: either on a date or after a count."""

    end_date: datetime | None = None
    occurrence_count: int | None = None


@dataclass(frozen=True)
class RecurrenceRule:
    """Defines a recurrence pattern for a calendar event."""

    frequency: RecurrenceFrequency = RecurrenceFrequency.WEEKLY
    interval: int = 1
    days_of_week: list[int] | None = None  # 1=Sunday .. 7=Saturday (EKWeekday)
    days_of_month: list[int] | None = None
    months_of_year: list[int] | None = None
    weeks_of_year: list[int] | None = None
    days_of_year: list[int] | None = None
    set_positions: list[int] | None = None
    end: RecurrenceEnd | None = None


@dataclass(frozen=True)
class Calendar:
    """A macOS calendar."""

    calendar_id: str
    title: str
    type: CalendarType
    color: str | None = None
    source: str | None = None
    is_immutable: bool = False
    allows_content_modifications: bool = True


@dataclass(frozen=True)
class Event:
    """A calendar event with all fields supported by macOS EventKit."""

    event_id: str
    title: str
    start: datetime
    end: datetime
    is_all_day: bool
    calendar: str
    calendar_id: str

    location: str | None = None
    structured_location: Location | None = None
    notes: str | None = None
    url: str | None = None
    time_zone: str | None = None

    availability: EventAvailability = EventAvailability.NOT_SUPPORTED
    status: EventStatus = EventStatus.NONE

    organizer: Participant | None = None
    attendees: list[Participant] = field(default_factory=list)
    alarms: list[Alarm] = field(default_factory=list)
    recurrence_rules: list[RecurrenceRule] = field(default_factory=list)

    creation_date: datetime | None = None
    last_modified_date: datetime | None = None
    is_recurring: bool = False
    is_detached: bool = False
    occurrence_date: datetime | None = None


@dataclass(frozen=True)
class TimeSlot:
    """A free time slot."""

    start: datetime
    end: datetime

    @property
    def duration(self) -> timedelta:
        return self.end - self.start
