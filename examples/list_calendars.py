"""Example: list all available macOS calendars."""

from maccal import CalendarStore

store = CalendarStore()

print("Available calendars:")
print("-" * 60)
for cal in store.list_calendars():
    print(f"  {cal.title:<30} type={cal.type.name:<12} source={cal.source}")
