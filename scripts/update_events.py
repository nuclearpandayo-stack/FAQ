import json
import os
import tempfile
import urllib.request

from datetime import datetime, timedelta, timezone
from pathlib import Path

from icalendar import Calendar
import recurring_ical_events


# =========================================================
# CONFIG
# =========================================================

CALENDAR_URL = os.environ["DARK_OMEN_CALENDAR_URL"]

OUTPUT_FILE = Path("data/events.json")

# How much of the calendar we publish.
PAST_DAYS = 7
FUTURE_DAYS = 90


# =========================================================
# DOWNLOAD CALENDAR
# =========================================================

def download_calendar():
    print("Downloading Dark Omen calendar...")

    request = urllib.request.Request(
        CALENDAR_URL,
        headers={
            "User-Agent": "Dark-Omen-Events/1.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        return response.read()


# =========================================================
# HELPERS
# =========================================================

def get_text(event, field):
    value = event.get(field)

    if value is None:
        return ""

    return str(value).strip()


def convert_date(value):
    """
    Convert an iCalendar date/datetime into the format
    used by our public events JSON.

    Timed events are converted to UTC.
    All-day events remain YYYY-MM-DD.
    """

    if value is None:
        return "", False

    value = value.dt

    # Timed event
    if isinstance(value, datetime):

        if value.tzinfo is None:
            value = value.replace(
                tzinfo=timezone.utc
            )

        value = value.astimezone(
            timezone.utc
        )

        return (
            value
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
            False
        )

    # All-day event
    return value.isoformat(), True


def convert_event(event):
    start, start_all_day = convert_date(
        event.get("DTSTART")
    )

    end, end_all_day = convert_date(
        event.get("DTEND")
    )

    if not end:
        end = start

    uid = get_text(
        event,
        "UID"
    )

    title = (
        get_text(event, "SUMMARY")
        or "Untitled Event"
    )

    status = get_text(
        event,
        "STATUS"
    ).lower()

    if not status:
        status = "confirmed"

    # UID alone is shared by recurring occurrences.
    # Combining it with the occurrence start gives every
    # event occurrence a stable unique ID.
    event_id = f"{uid}::{start}"

    return {
        "id": event_id,
        "title": title,
        "start": start,
        "end": end,
        "all_day": (
            start_all_day
            or end_all_day
        ),
        "description": get_text(
            event,
            "DESCRIPTION"
        ),
        "location": get_text(
            event,
            "LOCATION"
        ),
        "status": status
    }


def should_include_event(event):
    """
    Decide whether an event should appear on the
    Dark Omen website / public event feed.
    """

    title = event["title"].lower()

    # Member birthdays are stored on the clan calendar,
    # but aren't part of the public events board.
    if "birthday" in title:
        return False

    # Ignore events explicitly marked as cancelled
    # by Google Calendar.
    if event["status"] == "cancelled":
        return False

    return True


# =========================================================
# SAVE JSON
# =========================================================

def save_events(events):
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output = {
        "version": 1,

        "generated_at": (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        ),

        "event_count": len(events),

        "events": events
    }

    # Write to a temporary file first.
    # This prevents a failed run from corrupting
    # the existing events.json.
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=OUTPUT_FILE.parent,
        delete=False
    ) as temp:

        json.dump(
            output,
            temp,
            indent=2,
            ensure_ascii=False
        )

        temp.write("\n")

        temp_path = Path(
            temp.name
        )

    temp_path.replace(
        OUTPUT_FILE
    )


# =========================================================
# MAIN
# =========================================================

def main():
    raw_calendar = download_calendar()

    calendar = Calendar.from_ical(
        raw_calendar
    )

    now = datetime.now(
        timezone.utc
    )

    start_range = (
        now
        - timedelta(days=PAST_DAYS)
    )

    end_range = (
        now
        + timedelta(days=FUTURE_DAYS)
    )

    print(
        f"Reading events from "
        f"{start_range.date()} "
        f"to {end_range.date()}..."
    )

    # Expand recurring Google Calendar events
    # into individual occurrences.
    calendar_events = list(
        recurring_ical_events
        .of(calendar)
        .between(
            start_range,
            end_range
        )
    )

    events = []

    skipped_birthdays = 0
    skipped_cancelled = 0

    for calendar_event in calendar_events:

        event = convert_event(
            calendar_event
        )

        if not event["start"]:
            continue

        if "birthday" in event["title"].lower():
            skipped_birthdays += 1
            continue

        if event["status"] == "cancelled":
            skipped_cancelled += 1
            continue

        if should_include_event(event):
            events.append(
                event
            )

    # Sort oldest -> newest.
    events.sort(
        key=lambda event:
            event["start"]
    )

    save_events(
        events
    )

    print(
        f"Published {len(events)} clan events."
    )

    print(
        f"Skipped {skipped_birthdays} birthdays."
    )

    print(
        f"Skipped {skipped_cancelled} cancelled events."
    )

    print(
        f"Updated {OUTPUT_FILE} successfully."
    )


if __name__ == "__main__":
    main()