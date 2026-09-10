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

# Include a small amount of history and the next 90 days.
PAST_DAYS = 7
FUTURE_DAYS = 90


# =========================================================
# DOWNLOAD GOOGLE CALENDAR
# =========================================================

def download_calendar():

    print("========================================")
    print("DOWNLOADING DARK OMEN CALENDAR")
    print("========================================")

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

        print(
            f"HTTP status: {response.status}"
        )

        raw_data = response.read()

    print(
        f"Downloaded {len(raw_data)} bytes"
    )

    return raw_data


# =========================================================
# DATE CONVERSION
# =========================================================

def convert_date(value):

    if value is None:
        return "", False

    value = value.dt

    # Normal timed event
    if isinstance(value, datetime):

        # Google should normally provide timezone information.
        # If it doesn't, fall back to UTC.
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

    # Date-only / all-day event
    return (
        value.isoformat(),
        True
    )


# =========================================================
# ICALENDAR HELPERS
# =========================================================

def get_text(event, field):

    value = event.get(field)

    if value is None:
        return ""

    return str(value).strip()


def convert_event(event):

    start, start_all_day = convert_date(
        event.get("DTSTART")
    )

    end, end_all_day = convert_date(
        event.get("DTEND")
    )

    # Some calendar events may not contain DTEND.
    if not end:
        end = start

    uid = get_text(
        event,
        "UID"
    )

    status = get_text(
        event,
        "STATUS"
    ).lower()

    if not status:
        status = "confirmed"

    return {

        "id": uid,

        "title": (
            get_text(
                event,
                "SUMMARY"
            )
            or "Untitled Event"
        ),

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
# SAVE JSON
# =========================================================

def save_events(events):

    print()
    print("========================================")
    print("WRITING JSON")
    print("========================================")

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    generated_at = (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )

    output = {

        "version": 1,

        "generated_at": generated_at,

        "event_count": len(events),

        "events": events
    }

    print(
        f"Output file: {OUTPUT_FILE}"
    )

    print(
        f"Generated at: {generated_at}"
    )

    print(
        f"Events being written: {len(events)}"
    )

    # Write to temporary file first.
    #
    # This prevents us destroying the existing
    # good events.json if something fails halfway.

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

    print(
        "events.json successfully written."
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("========================================")
    print("DARK OMEN EVENT IMPORTER")
    print("========================================")
    print()

    # -----------------------------------------------------
    # Download
    # -----------------------------------------------------

    raw_calendar = download_calendar()

    print()

    # -----------------------------------------------------
    # Parse ICS
    # -----------------------------------------------------

    print("========================================")
    print("PARSING CALENDAR")
    print("========================================")

    calendar = Calendar.from_ical(
        raw_calendar
    )

    print(
        "Calendar parsed successfully."
    )

    # -----------------------------------------------------
    # Count RAW events
    # -----------------------------------------------------

    raw_events = list(
        calendar.walk("VEVENT")
    )

    print(
        f"Raw VEVENT count: {len(raw_events)}"
    )

    print()

    # -----------------------------------------------------
    # Show events Google actually returned
    # -----------------------------------------------------

    print("========================================")
    print("RAW EVENTS FROM GOOGLE")
    print("========================================")

    if not raw_events:

        print(
            "WARNING: Google returned ZERO VEVENT entries."
        )

    else:

        # Print first 20 so logs don't become ridiculous.
        for index, event in enumerate(
            raw_events[:20],
            start=1
        ):

            print(
                f"{index}. "
                f"{get_text(event, 'SUMMARY')}"
            )

            print(
                f"   DTSTART: "
                f"{event.get('DTSTART')}"
            )

            print(
                f"   DTEND: "
                f"{event.get('DTEND')}"
            )

            print(
                f"   STATUS: "
                f"{event.get('STATUS')}"
            )

            print()

    # -----------------------------------------------------
    # Determine our requested window
    # -----------------------------------------------------

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

    print("========================================")
    print("EVENT WINDOW")
    print("========================================")

    print(
        f"Current UTC time: {now}"
    )

    print(
        f"Looking from: {start_range}"
    )

    print(
        f"Looking until: {end_range}"
    )

    print()

    # -----------------------------------------------------
    # Expand recurring events
    # -----------------------------------------------------

    print("========================================")
    print("EXPANDING EVENTS")
    print("========================================")

    calendar_events = list(
        recurring_ical_events
        .of(calendar)
        .between(
            start_range,
            end_range
        )
    )

    print(
        f"Events inside requested window: "
        f"{len(calendar_events)}"
    )

    print()

    # -----------------------------------------------------
    # Convert to our public format
    # -----------------------------------------------------

    events = []

    for calendar_event in calendar_events:

        event = convert_event(
            calendar_event
        )

        if not event["start"]:

            print(
                "Skipping event with no start date:"
            )

            print(
                event["title"]
            )

            continue

        events.append(
            event
        )

    # -----------------------------------------------------
    # Sort chronologically
    # -----------------------------------------------------

    events.sort(
        key=lambda event:
            event["start"]
    )

    # -----------------------------------------------------
    # Show EXACTLY what we're about to publish
    # -----------------------------------------------------

    print("========================================")
    print("FINAL EVENTS")
    print("========================================")

    if not events:

        print(
            "WARNING: No events will be written."
        )

    else:

        for index, event in enumerate(
            events,
            start=1
        ):

            print(
                f"{index}. {event['title']}"
            )

            print(
                f"   Start: {event['start']}"
            )

            print(
                f"   End:   {event['end']}"
            )

            print(
                f"   All day: {event['all_day']}"
            )

            print(
                f"   Location: {event['location']}"
            )

            print()

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    save_events(
        events
    )

    print()
    print("========================================")
    print("COMPLETE")
    print("========================================")

    print(
        f"Done! {len(events)} events written "
        f"to {OUTPUT_FILE}"
    )

    print()


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()