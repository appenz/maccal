"""Tests for CalendarStore initialization and calendar listing.

These tests require macOS with calendar access granted.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")


class TestCalendarStore:
    def test_store_creates(self, store):
        assert store is not None
        assert store.ek_store is not None

    def test_list_calendars(self, store):
        calendars = store.list_calendars()
        assert isinstance(calendars, list)
        assert len(calendars) > 0
        for cal in calendars:
            assert cal.calendar_id
            assert cal.title

    def test_list_calendars_filter_type(self, store):
        local_cals = store.list_calendars(type="local")
        assert isinstance(local_cals, list)
        for cal in local_cals:
            from maccal import CalendarType

            assert cal.type == CalendarType.LOCAL

    def test_list_calendars_invalid_type(self, store):
        with pytest.raises(ValueError, match="Unknown calendar type"):
            store.list_calendars(type="nonexistent")

    def test_searchable_fields(self, store):
        assert "title" in store.SEARCHABLE_FIELDS
        assert "attendee_email" in store.SEARCHABLE_FIELDS
        assert len(store.SEARCHABLE_FIELDS) == 9
