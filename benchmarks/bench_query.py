"""Benchmark: measure EventKit query and search performance.

Creates a temporary calendar with synthetic events and times:
  1. EventKit fetch (raw ObjC objects)
  2. Full dataclass conversion
  3. Lazy text search (field-restricted)
  4. Broad text search (all fields)

Usage:
    uv run python -m benchmarks.bench_query
    uv run python -m benchmarks.bench_query --count 5000
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

if sys.platform != "darwin":
    print("This benchmark requires macOS.")
    sys.exit(1)

import EventKit
from Foundation import NSDate, NSRunLoop

from maccal._convert import datetime_to_nsdate, ek_event_to_event
from maccal.events import _ek_event_matches, _FIELD_EXTRACTORS


def get_store() -> EventKit.EKEventStore:
    store = EventKit.EKEventStore.alloc().init()
    done = threading.Event()
    granted_flag: list[bool] = []

    def cb(granted, error):
        granted_flag.append(granted)
        done.set()

    store.requestFullAccessToEventsWithCompletion_(cb)
    while not done.is_set():
        NSRunLoop.currentRunLoop().runUntilDate_(
            NSDate.dateWithTimeIntervalSinceNow_(0.05)
        )
    if not granted_flag or not granted_flag[0]:
        print("Calendar access denied.")
        sys.exit(1)
    return store


def create_test_calendar(store: EventKit.EKEventStore) -> EventKit.EKCalendar:
    source = None
    for s in store.sources():
        if s.sourceType() == 0:
            source = s
            break
    if source is None:
        print("No local calendar source.")
        sys.exit(1)

    cal = EventKit.EKCalendar.calendarForEntityType_eventStore_(0, store)
    cal.setTitle_("maccal-benchmark")
    cal.setSource_(source)
    store.saveCalendar_commit_error_(cal, True, None)
    return cal


def populate_events(
    store: EventKit.EKEventStore, cal: EventKit.EKCalendar, count: int
) -> tuple[datetime, datetime]:
    """Create `count` synthetic events spread over a date range. Returns (start, end)."""
    base = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)
    print(f"Creating {count} synthetic events...")
    t0 = time.perf_counter()

    for i in range(count):
        ev = EventKit.EKEvent.eventWithEventStore_(store)
        ev.setTitle_(f"Benchmark Event {i}")
        ev.setStartDate_(datetime_to_nsdate(base + timedelta(hours=i)))
        ev.setEndDate_(datetime_to_nsdate(base + timedelta(hours=i, minutes=45)))
        ev.setCalendar_(cal)
        ev.setLocation_(f"Room {i % 50}")
        ev.setNotes_(f"Synthetic event number {i} for benchmarking maccal library")
        store.saveEvent_span_error_(ev, EventKit.EKSpanThisEvent, None)

    elapsed = time.perf_counter() - t0
    print(f"  Created {count} events in {elapsed:.2f}s ({count / elapsed:.0f} events/s)")

    end = base + timedelta(hours=count + 1)
    return base, end


def bench_fetch(store, start, end, cal):
    """Benchmark raw EventKit fetch."""
    predicate = store.predicateForEventsWithStartDate_endDate_calendars_(
        datetime_to_nsdate(start), datetime_to_nsdate(end), [cal]
    )
    t0 = time.perf_counter()
    ek_events = store.eventsMatchingPredicate_(predicate)
    elapsed = time.perf_counter() - t0
    count = len(ek_events)
    print(f"  EventKit fetch:        {count} events in {elapsed * 1000:.1f}ms")
    return ek_events


def bench_convert(ek_events):
    """Benchmark full dataclass conversion."""
    t0 = time.perf_counter()
    events = [ek_event_to_event(e) for e in ek_events]
    elapsed = time.perf_counter() - t0
    print(f"  Full conversion:       {len(events)} events in {elapsed * 1000:.1f}ms")
    return events


def bench_lazy_search(ek_events, query="Benchmark Event 42"):
    """Benchmark lazy field-restricted search."""
    fields = ["title"]
    query_lower = query.lower()
    t0 = time.perf_counter()
    matches = [e for e in ek_events if _ek_event_matches(e, query_lower, fields)]
    elapsed = time.perf_counter() - t0
    converted = [ek_event_to_event(e) for e in matches]
    total = time.perf_counter() - t0
    print(
        f"  Lazy search (title):   {len(converted)} matches, "
        f"filter {elapsed * 1000:.1f}ms + convert {(total - elapsed) * 1000:.1f}ms "
        f"= {total * 1000:.1f}ms total"
    )


def bench_broad_search(ek_events, query="benchmark"):
    """Benchmark broad search across all fields."""
    all_fields = list(_FIELD_EXTRACTORS)
    query_lower = query.lower()
    t0 = time.perf_counter()
    matches = [e for e in ek_events if _ek_event_matches(e, query_lower, all_fields)]
    elapsed = time.perf_counter() - t0
    converted = [ek_event_to_event(e) for e in matches]
    total = time.perf_counter() - t0
    print(
        f"  Broad search (all):    {len(converted)} matches, "
        f"filter {elapsed * 1000:.1f}ms + convert {(total - elapsed) * 1000:.1f}ms "
        f"= {total * 1000:.1f}ms total"
    )


def cleanup(store, cal):
    store.removeCalendar_commit_error_(cal, True, None)


def main():
    parser = argparse.ArgumentParser(description="maccal query benchmarks")
    parser.add_argument("--count", type=int, default=1000, help="Number of events")
    args = parser.parse_args()

    print(f"maccal benchmark ({args.count} events)\n{'=' * 40}")

    store = get_store()
    cal = create_test_calendar(store)

    try:
        start, end = populate_events(store, cal, args.count)
        print()
        ek_events = bench_fetch(store, start, end, cal)
        bench_convert(ek_events)
        bench_lazy_search(ek_events)
        bench_broad_search(ek_events)
    finally:
        print("\nCleaning up...")
        cleanup(store, cal)

    print("Done.")


if __name__ == "__main__":
    main()
