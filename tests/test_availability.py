"""Tests for the availability (free time) computation logic.

These tests exercise the pure-Python interval merging and gap-finding,
which do not require EventKit.
"""

from datetime import UTC, datetime, timedelta

from maccal.availability import _find_gaps, _merge_intervals
from maccal.types import TimeSlot


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 3, 15, hour, minute, tzinfo=UTC)


class TestMergeIntervals:
    def test_empty(self):
        assert _merge_intervals([]) == []

    def test_no_overlap(self):
        intervals = [(_dt(9), _dt(10)), (_dt(11), _dt(12))]
        assert _merge_intervals(intervals) == intervals

    def test_overlap(self):
        intervals = [(_dt(9), _dt(11)), (_dt(10), _dt(12))]
        assert _merge_intervals(intervals) == [(_dt(9), _dt(12))]

    def test_adjacent(self):
        intervals = [(_dt(9), _dt(10)), (_dt(10), _dt(11))]
        assert _merge_intervals(intervals) == [(_dt(9), _dt(11))]

    def test_contained(self):
        intervals = [(_dt(9), _dt(14)), (_dt(10), _dt(12))]
        assert _merge_intervals(intervals) == [(_dt(9), _dt(14))]

    def test_unsorted_input(self):
        intervals = [(_dt(11), _dt(12)), (_dt(9), _dt(10))]
        assert _merge_intervals(intervals) == [(_dt(9), _dt(10)), (_dt(11), _dt(12))]

    def test_multiple_merges(self):
        intervals = [
            (_dt(9), _dt(10)),
            (_dt(9, 30), _dt(11)),
            (_dt(13), _dt(14)),
            (_dt(13, 30), _dt(15)),
        ]
        expected = [(_dt(9), _dt(11)), (_dt(13), _dt(15))]
        assert _merge_intervals(intervals) == expected


class TestFindGaps:
    def test_no_busy(self):
        slots = _find_gaps(_dt(9), _dt(17), [], timedelta(minutes=30))
        assert len(slots) == 1
        assert slots[0] == TimeSlot(start=_dt(9), end=_dt(17))

    def test_fully_busy(self):
        busy = [(_dt(9), _dt(17))]
        slots = _find_gaps(_dt(9), _dt(17), busy, timedelta(minutes=30))
        assert slots == []

    def test_gap_before_and_after(self):
        busy = [(_dt(11), _dt(13))]
        slots = _find_gaps(_dt(9), _dt(17), busy, timedelta(minutes=30))
        assert len(slots) == 2
        assert slots[0] == TimeSlot(start=_dt(9), end=_dt(11))
        assert slots[1] == TimeSlot(start=_dt(13), end=_dt(17))

    def test_gap_too_short(self):
        busy = [(_dt(9, 30), _dt(10)), (_dt(10, 15), _dt(17))]
        slots = _find_gaps(_dt(9), _dt(17), busy, timedelta(minutes=30))
        assert len(slots) == 1
        assert slots[0] == TimeSlot(start=_dt(9), end=_dt(9, 30))

    def test_multiple_gaps(self):
        busy = [(_dt(10), _dt(11)), (_dt(13), _dt(14)), (_dt(15), _dt(16))]
        slots = _find_gaps(_dt(9), _dt(17), busy, timedelta(minutes=30))
        assert len(slots) == 4
        assert slots[0].start == _dt(9)
        assert slots[1].start == _dt(11)
        assert slots[2].start == _dt(14)
        assert slots[3].start == _dt(16)

    def test_duration_property(self):
        slots = _find_gaps(_dt(9), _dt(10), [], timedelta(minutes=30))
        assert slots[0].duration == timedelta(hours=1)
