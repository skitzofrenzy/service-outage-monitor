#!/usr/bin/env python3
import os
import re
import sys
import csv
import uuid
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import requests
import yaml
import dateparser
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from dotenv import load_dotenv
from dateutil import tz

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
load_dotenv()

TZ = os.getenv("TZ", "America/Port_of_Spain")

def load_config(path="config.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def fetch(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; OutageMonitor/1.0; +https://example.com)"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text

def norm_text(t):
    return re.sub(r"\s+", " ", (t or "").strip())

def parse_datetime_range(text, explicit_formats=None, default_start="08:00", default_end="17:00", zone=TZ):
    """
    Attempts to parse a start and end datetime from provided text. If only a date is found,
    falls back to default start/end times. Returns (start_dt, end_dt) timezone-aware.
    """
    # Try explicit formats first, if provided (single date or datetime)
    if explicit_formats:
        for fmt in explicit_formats:
            try:
                # dateparser doesn't use strptime-style tokens; we'll try strict parsing via dateparser with settings
                dt = dateparser.parse(text, settings={"PREFER_DATES_FROM": "future"})
                if dt:
                    start = dt
                    # If no time included, apply default times
                    if start.hour == 0 and start.minute == 0 and re.search(r"\b00:00\b", text) is None:
                        start_time = dateparser.parse(default_start).time()
                        end_time = dateparser.parse(default_end).time()
                        start = datetime.combine(start.date(), start_time)
                        end = datetime.combine(start.date(), end_time)
                    else:
                        # Heuristic: if only one time found, set end = start + 2h
                        end = start + timedelta(hours=2)
                    return make_tzaware(start, zone), make_tzaware(end, zone)
            except Exception:
                pass

    # Fallback: find up to two time-like strings; let dateparser infer date(s)
    # Common patterns like "Oct 5, 2025 1:00 AM to 5:00 AM", "5 Oct 2025 01:00-05:00"
    time_patterns = re.findall(r"(\d{1,2}:\d{2}\s*(?:AM|PM)?)", text, flags=re.I)
    date_candidate = dateparser.parse(text, settings={"PREFER_DATES_FROM": "future"})
    if date_candidate:
        if len(time_patterns) >= 1:
            start_time = dateparser.parse(time_patterns[0]).time()
            start = datetime.combine(date_candidate.date(), start_time)
            if len(time_patterns) >= 2:
                end_time = dateparser.parse(time_patterns[1]).time()
                end = datetime.combine(date_candidate.date(), end_time)
            else:
                end = start + timedelta(hours=2)
            return make_tzaware(start, zone), make_tzaware(end, zone)

        # Only a date — apply defaults
        start_time = dateparser.parse(default_start).time()
        end_time = dateparser.parse(default_end).time()
        start = datetime.combine(date_candidate.date(), start_time)
        end = datetime.combine(date_candidate.date(), end_time)
        return make_tzaware(start, zone), make_tzaware(end, zone)

    return None, None

def make_tzaware(dt, zone):
    if dt.tzinfo is not None:
        return dt.astimezone(tz.gettz(zone))
    return dt.replace(tzinfo=tz.gettz(zone))

def build_ics(events, tzname=TZ):
    cal = Calendar()
    cal.add('prodid', '-//Outage Monitor//')
    cal.add('version', '2.0')
    cal.add('method', 'PUBLISH')

    for ev in events:
        e = Event()
        e.add('uid', ev.get("uid", str(uuid.uuid4())))
        e.add('summary', ev['summary'])
        e.add('dtstart', ev['start'])
        e.add('dtend', ev['end'])
        e.add('location', ev.get('location', ''))
        e.add('description', ev.get('description', ''))
        e.add('url', ev.get('url', ''))
        cal.add_component(e)

    return cal.to_ical()

def send_email_with_attachment(subject, body, attachment_bytes, filename):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd  = os.getenv("SMTP_PASS")
    from_email = os.getenv("FROM_EMAIL", user)
    to_email   = os.getenv("TO_EMAIL", user)

    if not all([host, port, user, pwd, from_email, to_email]):
        raise RuntimeError("SMTP env vars missing. See .env.example.")

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment_bytes)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
    msg.attach(part)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, pwd)
        server.sendmail(from_email, [to_email], msg.as_string())

def match_area(text, keywords):
    t = norm_text(text).lower()
    for kw in keywords:
        if kw.lower() in t:
            return True
    return False

def scrape_provider(p, default_tz):
    logging.info("Scraping: %s", p['name'])
    html = fetch(p['url'])
    soup = BeautifulSoup(html, "lxml")
    parsing = p['parsing']

    events = []
    if parsing.get('mode') == 'css':
        items = soup.select(parsing.get('item_selector', 'article'))
        for it in items:
            date_text = ""
            # Prefer explicit date selector if present
            ds = parsing.get('date_selector')
            if ds:
                el = it.select_one(ds)
                if el:
                    date_text = norm_text(el.get_text(" "))
            if not date_text:
                # If not found, try entire item text
                date_text = norm_text(it.get_text(" "))

            text_el = None
            ts = parsing.get('text_selector')
            if ts:
                text_el = it.select_one(ts)
            body_text = norm_text(text_el.get_text(" ") if text_el else it.get_text(" "))

            if not match_area(body_text, p.get('area_keywords', [])):
                continue

            start, end = parse_datetime_range(
                date_text + " " + body_text,
                explicit_formats=parsing.get('date_formats'),
                default_start=parsing.get('default_start_time', '08:00'),
                default_end=parsing.get('default_end_time', '17:00'),
                zone=default_tz
            )
            if not start or not end:
                logging.warning("Could not parse date for item on %s", p['name'])
                continue

            title = f"Scheduled {p['service']} outage – {p['name']}"
            ev = {
                "summary": title,
                "start": start,
                "end": end,
                "location": ", ".join(p.get('area_keywords', [])),
                "description": body_text[:800],
                "url": p['url'],
                "uid": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{p['url']}-{start.isoformat()}-{title}"))
            }
            events.append(ev)

    else:
        # Regex mode: scan full page text
        text = norm_text(soup.get_text(" "))
        if not match_area(text, p.get('area_keywords', [])):
            return []
        start, end = parse_datetime_range(
            text,
            explicit_formats=parsing.get('date_formats'),
            default_start=parsing.get('default_start_time', '08:00'),
            default_end=parsing.get('default_end_time', '17:00'),
            zone=default_tz
        )
        if start and end:
            events.append({
                "summary": f"Scheduled {p['service']} outage – {p['name']}",
                "start": start,
                "end": end,
                "location": ", ".join(p.get('area_keywords', [])),
                "description": text[:800],
                "url": p['url'],
                "uid": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{p['url']}-{start.isoformat()}"))
            })

    return events

def main():
    cfg = load_config()
    providers = cfg.get("providers", [])
    tzname = cfg.get("timezone", TZ)
    all_events = []
    for p in providers:
        try:
            all_events.extend(scrape_provider(p, tzname))
        except Exception as e:
            logging.exception("Provider failed: %s", p.get('name', 'unknown'))

    if not all_events:
        logging.info("No matching outages found this run.")
        return 0

    # Sort and de-duplicate by uid
    seen = set()
    unique = []
    for ev in sorted(all_events, key=lambda e: e['start']):
        if ev['uid'] in seen:
            continue
        seen.add(ev['uid'])
        unique.append(ev)

    ics_bytes = build_ics(unique, tzname)
    today = datetime.now().strftime("%Y%m%d")
    filename = f"scheduled-outages-{today}.ics"

    subject = f"[Outage Monitor] {len(unique)} event(s) found"
    body = "Attached is your weekly scheduled outage calendar file.\n\n— Outage Monitor"
    send_email_with_attachment(subject, body, ics_bytes, filename)

    # Also save locally in case running on a server
    with open(filename, "wb") as f:
        f.write(ics_bytes)
    logging.info("Wrote %s and emailed.", filename)
    return 0

if __name__ == "__main__":
    sys.exit(main())
