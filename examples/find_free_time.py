"""Example: find free time slots in a workday."""

from datetime import datetime, timedelta, timezone

from maccal import CalendarStore

store = CalendarStore()

tomorrow = datetime.now(tz=timezone.utc).replace(
    hour=9, minute=0, second=0, microsecond=0
) + timedelta(days=1)
end_of_day = tomorrow.replace(hour=17)

print(f"Free 30-minute slots on {tomorrow:%Y-%m-%d} (9am-5pm):\n")

slots = store.find_free_time(
    tomorrow,
    end_of_day,
    duration=timedelta(minutes=30),
)

for slot in slots:
    print(f"  {slot.start:%H:%M} - {slot.end:%H:%M}  ({slot.duration})")

if not slots:
    print("  No free slots found.")
