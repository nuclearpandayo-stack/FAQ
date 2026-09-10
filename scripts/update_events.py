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

# Publish a small amount of history for the calendar
# and the next 90 days of upcoming events.
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
    used by the public events JSON.

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


# =========================================================
# CONVERT EVENT
# =========================================================

def convert_event(event):
    start, start_all_day = convert_date(
        event.get("DTSTART")
    )

    end, end_all_day = convert_date(
        event.get("DTEND")
    )

    # Some calendar events may not have DTEND.
    if not end:
        end = start

    uid = get_text(
        event,
        "UID"
    )

    title = (
        get_text(
            event,
            "SUMMARY"
        )
        or "Untitled Event"
    )

    status = get_text(
        event,
        "STATUS"
    ).lower()

    if not status:
        status = "confirmed"

    # Recurring occurrences share the same Google UID.
    # Combining UID + start gives each occurrence its
    # own stable ID.
    event_id = (
        f"{uid}::{start}"
    )

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


# =========================================================
# EVENT FILTERING
# =========================================================

def get_exclusion_reason(event):
    """
    Return the reason an event should be excluded.

    Returns None when the event should be published.
    """

    title = (
        event["title"]
        .strip()
        .lower()
    )

    status = (
        event["status"]
        .strip()
        .lower()
    )

    # -----------------------------------------------------
    # BIRTHDAYS
    # -----------------------------------------------------

    if "birthday" in title:
        return "birthday"

    # -----------------------------------------------------
    # GOOGLE-CANCELLED EVENTS
    # -----------------------------------------------------

    if status == "cancelled":
        return "cancelled"

    # -----------------------------------------------------
    # MANUALLY CANCELLED EVENTS
    #
    # Some events are not actually marked CANCELLED in
    # Google Calendar. Instead the organiser has renamed
    # them:
    #
    #   Canceled - Castlewars - 9PM GMT
    #   Cancelled - PvM Event
    #
    # These should also disappear from the website/feed.
    # -----------------------------------------------------

    if (
        title.startswith("cancelled")
        or title.startswith("canceled")
    ):
        return "cancelled"

    return None


def should_include_event(event):
    return (
        get_exclusion_reason(event)
        is None
    )


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
    #
    # If something goes wrong while writing, the
    # previously working events.json remains intact.

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
        - timedelta(
            days=PAST_DAYS
        )
    )

    end_range = (
        now
        + timedelta(
            days=FUTURE_DAYS
        )
    )

    print(
        f"Reading events from "
        f"{start_range.date()} "
        f"to {end_range.date()}..."
    )

    # -----------------------------------------------------
    # EXPAND RECURRING EVENTS
    # -----------------------------------------------------

    calendar_events = list(
        recurring_ical_events
        .of(calendar)
        .between(
            start_range,
            end_range
        )
    )

    # -----------------------------------------------------
    # FILTER + CONVERT
    # -----------------------------------------------------

    events = []

    skipped_birthdays = 0
    skipped_cancelled = 0
    skipped_invalid = 0

    for calendar_event in calendar_events:

        event = convert_event(
            calendar_event
        )

        # Event has no usable start date.
        if not event["start"]:

            skipped_invalid += 1

            continue

        exclusion_reason = (
            get_exclusion_reason(
                event
            )
        )

        if exclusion_reason == "birthday":

            skipped_birthdays += 1

            continue

        if exclusion_reason == "cancelled":

            skipped_cancelled += 1

            continue

        events.append(
            event
        )

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    events.sort(
        key=lambda event:
            event["start"]
    )

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    save_events(
        events
    )

    # -----------------------------------------------------
    # LOG
    # -----------------------------------------------------

    print()

    print(
        f"Published {len(events)} clan events."
    )

    print(
        f"Skipped {skipped_birthdays} birthdays."
    )

    print(
        f"Skipped {skipped_cancelled} cancelled events."
    )

    if skipped_invalid > 0:

        print(
            f"Skipped {skipped_invalid} invalid events."
        )

    print(
        f"Updated {OUTPUT_FILE} successfully."
    )


if __name__ == "__main__":
    main()