"""Tests for event CRUD and search operations.

These tests require macOS with calendar access granted and use a temporary
test calendar (see conftest.py).
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")


class TestGetEvents:
    def test_get_events_returns_list(self, store, sample_event):
        now = datetime.now(tz=UTC)
        events = store.get_events(
            now - timedelta(hours=1),
            now + timedelta(hours=24),
        )
        assert isinstance(events, list)
        assert len(events) > 0

    def test_get_events_finds_sample(self, store, sample_event, test_calendar):
        cal_name = str(test_calendar.title())
        now = datetime.now(tz=UTC)
        events = store.get_events(
            now - timedelta(hours=1),
            now + timedelta(hours=24),
            calendars=[cal_name],
        )
        titles = [e.title for e in events]
        assert "maccal test event" in titles

    def test_get_events_returns_list_for_any_range(self, store):
        far_future = datetime(2099, 1, 1, tzinfo=UTC)
        events = store.get_events(
            far_future,
            far_future + timedelta(hours=1),
        )
        assert isinstance(events, list)


class TestFindEvents:
    def test_find_by_title(self, store, sample_event, test_calendar):
        cal_name = str(test_calendar.title())
        now = datetime.now(tz=UTC)
        events = store.find_events(
            "maccal test",
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=24),
            calendars=[cal_name],
            fields=["title"],
        )
        assert len(events) >= 1
        assert all("maccal test" in e.title.lower() for e in events)

    def test_find_by_location(self, store, sample_event, test_calendar):
        cal_name = str(test_calendar.title())
        now = datetime.now(tz=UTC)
        events = store.find_events(
            "Room 42",
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=24),
            calendars=[cal_name],
            fields=["location"],
        )
        assert len(events) >= 1

    def test_find_by_notes(self, store, sample_event, test_calendar):
        cal_name = str(test_calendar.title())
        now = datetime.now(tz=UTC)
        events = store.find_events(
            "maccal test suite",
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=24),
            calendars=[cal_name],
            fields=["notes"],
        )
        assert len(events) >= 1

    def test_find_all_fields(self, store, sample_event, test_calendar):
        cal_name = str(test_calendar.title())
        now = datetime.now(tz=UTC)
        events = store.find_events(
            "maccal test",
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=24),
            calendars=[cal_name],
        )
        assert len(events) >= 1

    def test_find_no_results(self, store, test_calendar):
        cal_name = str(test_calendar.title())
        now = datetime.now(tz=UTC)
        events = store.find_events(
            "xyznonexistent999",
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=24),
            calendars=[cal_name],
        )
        assert events == []

    def test_find_invalid_field(self, store):
        now = datetime.now(tz=UTC)
        with pytest.raises(ValueError, match="Unknown search fields"):
            store.find_events(
                "test",
                start=now,
                end=now + timedelta(hours=1),
                fields=["nonexistent_field"],
            )


class TestAddAndDeleteEvent:
    def test_add_minimal_event(self, store, test_calendar):
        cal_name = str(test_calendar.title())
        now = datetime.now(tz=UTC)
        event = store.add_event(
            title="maccal add test",
            start=now + timedelta(hours=5),
            end=now + timedelta(hours=6),
            calendar=cal_name,
        )
        assert event.event_id
        assert event.title == "maccal add test"
        assert event.calendar == cal_name

        store.delete_event(event.event_id)

    def test_add_event_with_details(self, store, test_calendar):
        from maccal import Alarm

        cal_name = str(test_calendar.title())
        now = datetime.now(tz=UTC)
        event = store.add_event(
            title="maccal detailed test",
            start=now + timedelta(hours=5),
            end=now + timedelta(hours=6),
            calendar=cal_name,
            location="Conference Room A",
            notes="Test notes",
            is_all_day=False,
            alarms=[Alarm(minutes_before=10)],
        )
        assert event.location == "Conference Room A"
        assert event.notes == "Test notes"
        alarm_minutes = [a.minutes_before for a in event.alarms]
        assert 10.0 in alarm_minutes

        store.delete_event(event.event_id)

    def test_add_event_invalid_calendar(self, store):
        now = datetime.now(tz=UTC)
        with pytest.raises(ValueError, match="not found"):
            store.add_event(
                title="should fail",
                start=now + timedelta(hours=5),
                end=now + timedelta(hours=6),
                calendar="nonexistent-calendar-xyz",
            )


class TestUpdateEvent:
    def test_update_title(self, store, test_calendar):
        cal_name = str(test_calendar.title())
        now = datetime.now(tz=UTC)
        event = store.add_event(
            title="original title",
            start=now + timedelta(hours=5),
            end=now + timedelta(hours=6),
            calendar=cal_name,
        )

        updated = store.update_event(event.event_id, title="updated title")
        assert updated.title == "updated title"

        store.delete_event(event.event_id)

    def test_update_nonexistent(self, store):
        with pytest.raises(ValueError, match="not found"):
            store.update_event("nonexistent-id-xyz", title="fail")
