# calendar/calendar_util.py
import logging
import uuid
import os
import re
from datetime import datetime, timedelta
from icalendar import Calendar, Event

def build_ics(events, tzname="America/Port_of_Spain", logger=None):
    cal = Calendar()
    cal.add('prodid', '-//Outage Monitor//')
    cal.add('version', '2.0')
    cal.add('method', 'PUBLISH')

    for ev in events:
        e = Event()
        e.add('uid', ev.get("uid", str(uuid.uuid4())))
        e.add('summary', ev['title'])  # e.g., TTEC - Scheduled Outage
        e.add('dtstart', ev['start'])
        e.add('dtend', ev['end'])
        e.add('location', ev.get('location', ''))
        e.add('description', ev.get('description', ''))
        e.add('url', ev.get('url', ''))
        cal.add_component(e)

    return cal.to_ical()


def create_event(date, time, title, status, location, description, logger=None):
    # Log the time input for debugging
    # if logger:
    #     logger.debug(f"Raw time data: {time}")

    # Manually replace a.m. and p.m. with AM and PM for proper parsing
    time = re.sub(r"\s*a\.m\.\s*", " AM", time, flags=re.IGNORECASE)
    time = re.sub(r"\s*p\.m\.\s*", " PM", time, flags=re.IGNORECASE)

    # Log the cleaned time for debugging
    # if logger:
    #     logger.debug(f"Cleaned time data: {time}")

    # If the time includes a range (e.g., "9:00 AM to 3:00 PM"), split it into start and end times
    if "to" in time:
        time_range = time.split("to")
        start_time = time_range[0].strip()
        end_time = time_range[1].strip()
    else:
        start_time = time
        end_time = time  # If no range, use the same time for start and end

    # Log the split times for debugging
    # if logger:
    #     logger.debug(f"Start time: {start_time}, End time: {end_time}")

    # Ensure time is in a proper format, adding AM/PM if missing
    for t in [start_time, end_time]:
        if len(t.split(":")) == 1:  # Only hour provided, add :00 and AM
            t = f"{t}:00"

        if not re.search(r"\bAM\b|\bPM\b", t, re.I):  # Check if AM/PM is missing
            hour = int(t.split(":")[0])
            if hour < 12:
                t = f"{t} AM"  # Default to AM if no AM/PM is found and the hour is before 12
            else:
                t = f"{t} PM"  # Default to PM if the hour is 12 or greater

        # Log the finalized time for debugging
        # if logger:
        #     logger.debug(f"Final time with AM/PM: {t}")

    # Combine date and time to create a datetime object
    try:
        start = datetime.strptime(f"{date} {start_time}", "%d/%m/%Y %I:%M %p")
        end = datetime.strptime(f"{date} {end_time}", "%d/%m/%Y %I:%M %p")
        
        # Log the finalized time for debugging
        # if logger:
        #     logger.debug(f"Start time: {start}, End time: {end}")
    except ValueError as e:
        # In case of a parsing issue, log it and skip this entry
        if logger:
            logger.warning(f"Skipping invalid event date/time: {date} {start_time} to {end_time} ({e})")
        start = end = None
    
    if not start or not end:
        # If we couldn't parse the time correctly, skip this event
        return None

    # If the status is 'Cancelled', modify the title and description
    if status.lower() == "cancelled":
        title = f"Cancelled: {title}"
        description = f"Cancelled: {description}"

    # Create event dictionary
    event = {
        'start': start,
        'end': end,
        'title': f"{title} - Scheduled Outage",
        'location': location,
        'description': f"{status}: {description}",
        'uid': str(uuid.uuid4())
    }
    
    return event

def save_ics_file(events, output_filename, logger=None):
    ics_data = build_ics(events, logger=logger)
    with open(output_filename, "wb") as f:
        f.write(ics_data)
    if logger:
        logger.info(f"ICS file saved: {output_filename}")
    return output_filename
