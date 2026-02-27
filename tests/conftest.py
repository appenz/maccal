"""Shared fixtures for maccal tests.

Uses the system's default calendar for test events. All test events are
created with a distinctive prefix and cleaned up after each test.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta

import pytest

skip_if_not_macos = pytest.mark.skipif(
    sys.platform != "darwin", reason="macOS only"
)

pytestmark = skip_if_not_macos


@pytest.fixture(scope="session")
def ek_store():
    """Session-scoped EKEventStore with calendar access."""
    import threading

    import EventKit
    from Foundation import NSDate, NSRunLoop

    store = EventKit.EKEventStore.alloc().init()
    granted_flag: list[bool] = []
    done = threading.Event()

    def callback(granted, error):
        granted_flag.append(granted)
        done.set()

    store.requestFullAccessToEventsWithCompletion_(callback)
    while not done.is_set():
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.05)
        )

    if not granted_flag or not granted_flag[0]:
        pytest.skip("Calendar access not granted")

    return store


@pytest.fixture(scope="session")
def test_calendar(ek_store):
    """Get the default writable calendar for test events."""
    cal = ek_store.defaultCalendarForNewEvents()
    if cal is None:
        pytest.skip("No default calendar available for new events")
    return cal


@pytest.fixture(scope="session")
def store():
    """Session-scoped CalendarStore instance."""
    from maccal import CalendarStore

    try:
        return CalendarStore()
    except Exception:
        pytest.skip("Could not create CalendarStore (permission denied?)")


@pytest.fixture()
def sample_event(ek_store, test_calendar):
    """Create a single test event in the default calendar, clean up after."""
    import EventKit

    from maccal._convert import datetime_to_nsdate

    now = datetime.now(tz=UTC)
    event = EventKit.EKEvent.eventWithEventStore_(ek_store)
    event.setTitle_("maccal test event")
    event.setStartDate_(datetime_to_nsdate(now + timedelta(hours=1)))
    event.setEndDate_(datetime_to_nsdate(now + timedelta(hours=2)))
    event.setCalendar_(test_calendar)
    event.setNotes_("Created by maccal test suite")
    event.setLocation_("Test Room 42")

    ek_store.saveEvent_span_error_(event, EventKit.EKSpanThisEvent, None)

    yield event

    try:
        ek_store.removeEvent_span_error_(event, EventKit.EKSpanThisEvent, None)
    except Exception:
        pass
