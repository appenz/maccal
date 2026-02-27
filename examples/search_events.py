"""Example: search for calendar events by keyword."""

from datetime import datetime, timedelta, timezone

from maccal import CalendarStore

store = CalendarStore()

now = datetime.now(tz=timezone.utc)
start = now - timedelta(days=30)
end = now + timedelta(days=30)

query = "meeting"
print(f'Searching for "{query}" in the next 30 days...\n')

events = store.find_events(query, start=start, end=end)

for event in events:
    print(f"  {event.start:%Y-%m-%d %H:%M}  {event.title}")
    if event.location:
        print(f"    Location: {event.location}")
    if event.attendees:
        names = [a.name or a.email or "?" for a in event.attendees]
        print(f"    Attendees: {', '.join(names)}")
    print()

print(f"Found {len(events)} events.")
