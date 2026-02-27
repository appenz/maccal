# macCal

A Python library to access local macOS calendars via EventKit and PyObjC. Works with macOS 26 Tahoe.

## Overview

- Written in 100% python, easy to audit and extend
- Can search events, find free time, add/edit/delete events
- Fully typed
- Apache 2.0

Written by Guido Appenzeller, guido@appenzeller.net. Feedback and PR's welcome.

## Requirements

- macOS 14+ (Sonoma or later)
- Python 13, but probably works with earlier versions
- Calendar access permission

## Installation

With uv

```bash
pip install maccal
```

For development:

```bash
git clone https://github.com/your-org/maccal.git
cd maccal
make install
```

## Quick Start

```python
from datetime import datetime, timedelta, timezone
from maccal import CalendarStore

store = CalendarStore()

# List calendars
for cal in store.list_calendars():
    print(f"{cal.title} ({cal.type.name})")

# Get events for the next 7 days
now = datetime.now(tz=timezone.utc)
events = store.get_events(now, now + timedelta(days=7))
for event in events:
    print(f"{event.start:%H:%M} {event.title}")

# Search events
results = store.find_events("standup", start=now, end=now + timedelta(days=30))

# Search specific fields
results = store.find_events(
    "@acme.com",
    start=now, end=now + timedelta(days=30),
    fields=["attendee_email"],
)

# Create an event
event = store.add_event(
    title="Team Lunch",
    start=datetime(2026, 3, 15, 12, 0, tzinfo=timezone.utc),
    end=datetime(2026, 3, 15, 13, 0, tzinfo=timezone.utc),
    calendar="Personal",
    location="Cafe",
)

# Find free time
slots = store.find_free_time(
    start=datetime(2026, 3, 15, 9, 0, tzinfo=timezone.utc),
    end=datetime(2026, 3, 15, 17, 0, tzinfo=timezone.utc),
    duration=timedelta(minutes=30),
)
```

## Searchable Fields

When using `find_events`, you can restrict search to specific fields:

- `title`, `location`, `notes`, `url`, `calendar`
- `organizer_name`, `organizer_email`
- `attendee_name`, `attendee_email`

Pass `fields=None` (default) to search all fields.

## Recurring Events

When querying events, recurring events are automatically expanded into individual
occurrences. When editing or deleting a recurring event, you must specify which
occurrences to affect:

```python
store.update_event(
    event.event_id,
    title="New Title",
    span="this",        # "this" or "future"
    occurrence_date=event.occurrence_date,
)
```

Omitting `occurrence_date` for a recurring event raises `ValueError`.

## Development

```bash
make install    # Install with dev dependencies
make test       # Run tests
make lint       # Check code style
make format     # Auto-format code
make build      # Build package
make benchmark  # Run performance benchmarks
```

## License

Apache 2.0. See [LICENSE](LICENSE).
