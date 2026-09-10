const EVENTS_URL = "./data/events.json";

let clanEvents = [];

let calendarDate = new Date();


// =========================================================
// ELEMENTS
// =========================================================

const upcomingViewButton =
    document.getElementById("upcomingViewButton");

const calendarViewButton =
    document.getElementById("calendarViewButton");

const upcomingView =
    document.getElementById("upcomingView");

const calendarView =
    document.getElementById("calendarView");

const eventsList =
    document.getElementById("eventsList");

const eventsCount =
    document.getElementById("eventsCount");

const eventsUpdated =
    document.getElementById("eventsUpdated");

const eventsError =
    document.getElementById("eventsError");

const calendarGrid =
    document.getElementById("calendarGrid");

const calendarMonthTitle =
    document.getElementById("calendarMonthTitle");

const previousMonthButton =
    document.getElementById("previousMonthButton");

const nextMonthButton =
    document.getElementById("nextMonthButton");

const calendarSelected =
    document.getElementById("calendarSelected");

const selectedDateTitle =
    document.getElementById("selectedDateTitle");

const selectedDateEvents =
    document.getElementById("selectedDateEvents");


// =========================================================
// LOAD EVENTS
// =========================================================

async function loadEvents() {

    try {

        const response = await fetch(
            EVENTS_URL,
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`
            );
        }

        const data = await response.json();

        clanEvents = Array.isArray(data.events)
            ? data.events
            : [];

        updateGeneratedTime(
            data.generated_at
        );

        renderUpcomingEvents();

        renderCalendar();

    }

    catch (error) {

        console.error(
            "Unable to load clan events:",
            error
        );

        upcomingView.hidden = true;

        calendarView.hidden = true;

        eventsError.hidden = false;

        eventsUpdated.textContent =
            "Calendar unavailable";

    }

}


// =========================================================
// DATE HELPERS
// =========================================================

function isAllDay(event) {

    return event.all_day === true;

}


function parseEventDate(value, allDay = false) {

    if (!value) {
        return null;
    }

    /*
        YYYY-MM-DD is deliberately parsed manually.

        new Date("2026-09-12") is interpreted as UTC
        by browsers and can move to another day depending
        on the visitor's timezone.
    */

    if (
        allDay &&
        /^\d{4}-\d{2}-\d{2}$/.test(value)
    ) {

        const [year, month, day] =
            value.split("-").map(Number);

        return new Date(
            year,
            month - 1,
            day
        );

    }

    return new Date(value);

}


function startOfToday() {

    const today = new Date();

    today.setHours(
        0,
        0,
        0,
        0
    );

    return today;

}


function formatDate(date) {

    return new Intl.DateTimeFormat(
        "en-GB",
        {
            weekday: "short",
            day: "numeric",
            month: "short"
        }
    ).format(date);

}


function formatLongDate(date) {

    return new Intl.DateTimeFormat(
        "en-GB",
        {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric"
        }
    ).format(date);

}


function formatMonth(date) {

    return new Intl.DateTimeFormat(
        "en-GB",
        {
            month: "long",
            year: "numeric"
        }
    ).format(date);

}


function formatGameTime(date) {

    return new Intl.DateTimeFormat(
        "en-GB",
        {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
            timeZone: "UTC"
        }
    ).format(date);

}


// =========================================================
// EVENT STATE
// =========================================================

function isPastEvent(event) {

    const end = parseEventDate(
        event.end || event.start,
        isAllDay(event)
    );

    if (!end) {
        return false;
    }

    return end < new Date();

}


function getUpcomingEvents() {

    return clanEvents
        .filter(event => !isPastEvent(event))
        .sort(
            (a, b) => {

                const aDate = parseEventDate(
                    a.start,
                    isAllDay(a)
                );

                const bDate = parseEventDate(
                    b.start,
                    isAllDay(b)
                );

                return aDate - bDate;

            }
        );

}


// =========================================================
// GENERATED TIME
// =========================================================

function updateGeneratedTime(value) {

    if (!value) {

        eventsUpdated.textContent =
            "Synced with clan calendar";

        return;

    }

    const date = new Date(value);

    eventsUpdated.textContent =
        `Last synced ${date.toLocaleString(
            "en-GB",
            {
                day: "numeric",
                month: "short",
                hour: "2-digit",
                minute: "2-digit"
            }
        )}`;

}


// =========================================================
// EVENT CARD
// =========================================================

function createEventCard(event, compact = false) {

    const start = parseEventDate(
        event.start,
        isAllDay(event)
    );

    const article =
        document.createElement("article");

    article.className =
        compact
            ? "event-card event-card-compact"
            : "event-card";


    // DATE BLOCK

    const dateBlock =
        document.createElement("div");

    dateBlock.className =
        "event-date-block";


    const month =
        document.createElement("span");

    month.className =
        "event-date-month";

    month.textContent =
        start
            ? start
                .toLocaleDateString(
                    "en-GB",
                    {
                        month: "short"
                    }
                )
                .toUpperCase()
            : "";


    const day =
        document.createElement("strong");

    day.className =
        "event-date-day";

    day.textContent =
        start
            ? start.getDate()
            : "—";


    const weekday =
        document.createElement("span");

    weekday.className =
        "event-date-weekday";

    weekday.textContent =
        start
            ? start
                .toLocaleDateString(
                    "en-GB",
                    {
                        weekday: "short"
                    }
                )
                .toUpperCase()
            : "";


    dateBlock.append(
        month,
        day,
        weekday
    );


    // CONTENT

    const content =
        document.createElement("div");

    content.className =
        "event-card-content";


    const meta =
        document.createElement("div");

    meta.className =
        "event-meta";


    const time =
        document.createElement("span");

    time.className =
        "event-time";


    if (isAllDay(event)) {

        time.textContent =
            "All Day";

    }

    else {

        time.textContent =
            `${formatGameTime(start)} Game Time`;

    }


    meta.appendChild(time);


    if (event.location) {

        const location =
            document.createElement("span");

        location.className =
            "event-location";

        location.textContent =
            event.location;

        meta.appendChild(location);

    }


    const title =
        document.createElement("h3");

    title.textContent =
        event.title;


    content.append(
        meta,
        title
    );


    if (event.description) {

        const description =
            document.createElement("p");

        description.className =
            "event-description";

        description.textContent =
            event.description;

        content.appendChild(
            description
        );

    }


    // STATUS

    const status =
        document.createElement("div");

    status.className =
        "event-status";

    status.innerHTML =
        "<span></span> Scheduled";


    article.append(
        dateBlock,
        content,
        status
    );

    return article;

}


// =========================================================
// UPCOMING EVENTS
// =========================================================

function renderUpcomingEvents() {

    const upcoming =
        getUpcomingEvents();

    eventsList.innerHTML = "";

    eventsCount.textContent =
        `${upcoming.length} ${
            upcoming.length === 1
                ? "event"
                : "events"
        }`;


    if (upcoming.length === 0) {

        eventsList.innerHTML = `
            <div class="events-empty">
                <div class="events-empty-icon">☾</div>
                <h3>No upcoming events</h3>
                <p>
                    Nothing is currently scheduled.
                    Check back soon.
                </p>
            </div>
        `;

        return;

    }


    upcoming.forEach(
        event => {

            eventsList.appendChild(
                createEventCard(event)
            );

        }
    );

}


// =========================================================
// CALENDAR
// =========================================================

function renderCalendar() {

    calendarGrid.innerHTML = "";

    calendarMonthTitle.textContent =
        formatMonth(calendarDate);


    const year =
        calendarDate.getFullYear();

    const month =
        calendarDate.getMonth();


    const firstDay =
        new Date(
            year,
            month,
            1
        );


    const daysInMonth =
        new Date(
            year,
            month + 1,
            0
        ).getDate();


    /*
        JS:
        Sunday = 0
        Monday = 1

        Our calendar:
        Monday = column 0
    */

    let startOffset =
        firstDay.getDay() - 1;

    if (startOffset < 0) {
        startOffset = 6;
    }


    const previousMonthDays =
        new Date(
            year,
            month,
            0
        ).getDate();


    const totalCells = 42;


    for (
        let cellIndex = 0;
        cellIndex < totalCells;
        cellIndex++
    ) {

        let dayNumber;

        let cellMonth = month;

        let cellYear = year;

        let outsideMonth = false;


        if (cellIndex < startOffset) {

            dayNumber =
                previousMonthDays
                - startOffset
                + cellIndex
                + 1;

            cellMonth =
                month - 1;

            outsideMonth = true;

        }

        else if (
            cellIndex >=
            startOffset + daysInMonth
        ) {

            dayNumber =
                cellIndex
                - startOffset
                - daysInMonth
                + 1;

            cellMonth =
                month + 1;

            outsideMonth = true;

        }

        else {

            dayNumber =
                cellIndex
                - startOffset
                + 1;

        }


        const cellDate =
            new Date(
                cellYear,
                cellMonth,
                dayNumber
            );


        const dayEvents =
            getEventsForDate(
                cellDate
            );


        const cell =
            createCalendarCell(
                cellDate,
                dayEvents,
                outsideMonth
            );


        calendarGrid.appendChild(
            cell
        );

    }

}


// =========================================================
// EVENTS ON DATE
// =========================================================

function getEventsForDate(date) {

    const target =
        new Date(
            date.getFullYear(),
            date.getMonth(),
            date.getDate()
        );


    return clanEvents.filter(
        event => {

            const start =
                parseEventDate(
                    event.start,
                    isAllDay(event)
                );

            const end =
                parseEventDate(
                    event.end || event.start,
                    isAllDay(event)
                );


            if (!start || !end) {
                return false;
            }


            const startDay =
                new Date(
                    start.getFullYear(),
                    start.getMonth(),
                    start.getDate()
                );


            let endDay =
                new Date(
                    end.getFullYear(),
                    end.getMonth(),
                    end.getDate()
                );


            /*
                iCalendar all-day DTEND is exclusive.

                Example:
                start 10 Sep
                end   11 Sep

                means the event only occurs on 10 Sep.
            */

            if (isAllDay(event)) {

                endDay.setDate(
                    endDay.getDate() - 1
                );

            }


            return (
                target >= startDay &&
                target <= endDay
            );

        }
    );

}


// =========================================================
// CALENDAR CELL
// =========================================================

function createCalendarCell(
    date,
    events,
    outsideMonth
) {

    const cell =
        document.createElement("button");

    cell.type = "button";

    cell.className =
        "calendar-day";


    if (outsideMonth) {

        cell.classList.add(
            "calendar-day-outside"
        );

    }


    const today =
        startOfToday();


    if (
        date.getFullYear() ===
            today.getFullYear() &&

        date.getMonth() ===
            today.getMonth() &&

        date.getDate() ===
            today.getDate()
    ) {

        cell.classList.add(
            "calendar-day-today"
        );

    }


    if (events.length > 0) {

        cell.classList.add(
            "calendar-day-has-events"
        );

    }


    const number =
        document.createElement("span");

    number.className =
        "calendar-day-number";

    number.textContent =
        date.getDate();


    const eventContainer =
        document.createElement("div");

    eventContainer.className =
        "calendar-day-events";


    events
        .slice(0, 3)
        .forEach(
            event => {

                const eventLabel =
                    document.createElement("span");

                eventLabel.className =
                    "calendar-event-label";

                eventLabel.textContent =
                    event.title;

                eventContainer.appendChild(
                    eventLabel
                );

            }
        );


    if (events.length > 3) {

        const more =
            document.createElement("span");

        more.className =
            "calendar-event-more";

        more.textContent =
            `+${events.length - 3} more`;

        eventContainer.appendChild(
            more
        );

    }


    cell.append(
        number,
        eventContainer
    );


    cell.addEventListener(
        "click",
        () => {

            showSelectedDate(
                date,
                events
            );

        }
    );


    return cell;

}


// =========================================================
// SELECTED DATE
// =========================================================

function showSelectedDate(
    date,
    events
) {

    calendarSelected.hidden =
        false;

    selectedDateTitle.textContent =
        formatLongDate(date);

    selectedDateEvents.innerHTML =
        "";


    if (events.length === 0) {

        selectedDateEvents.innerHTML = `
            <div class="events-empty events-empty-small">
                <p>No events scheduled for this day.</p>
            </div>
        `;

    }

    else {

        events.forEach(
            event => {

                selectedDateEvents.appendChild(
                    createEventCard(
                        event,
                        true
                    )
                );

            }
        );

    }


    calendarSelected.scrollIntoView({
        behavior: "smooth",
        block: "nearest"
    });

}


// =========================================================
// VIEW SWITCHING
// =========================================================

function showUpcomingView() {

    upcomingView.hidden = false;

    calendarView.hidden = true;

    upcomingViewButton
        .classList.add("active");

    calendarViewButton
        .classList.remove("active");

}


function showCalendarView() {

    upcomingView.hidden = true;

    calendarView.hidden = false;

    calendarViewButton
        .classList.add("active");

    upcomingViewButton
        .classList.remove("active");

    renderCalendar();

}


// =========================================================
// MONTH NAVIGATION
// =========================================================

function changeMonth(amount) {

    calendarDate =
        new Date(
            calendarDate.getFullYear(),
            calendarDate.getMonth() + amount,
            1
        );

    calendarSelected.hidden =
        true;

    renderCalendar();

}


// =========================================================
// LISTENERS
// =========================================================

upcomingViewButton.addEventListener(
    "click",
    showUpcomingView
);


calendarViewButton.addEventListener(
    "click",
    showCalendarView
);


previousMonthButton.addEventListener(
    "click",
    () => changeMonth(-1)
);


nextMonthButton.addEventListener(
    "click",
    () => changeMonth(1)
);


// =========================================================
// START
// =========================================================

loadEvents();