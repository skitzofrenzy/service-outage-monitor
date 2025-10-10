# main.py
from datetime import datetime
from html import escape
import yaml

from .utils.my_logging import setup_logging
from .utils.env_util import recipients_for_provider
from .scraping.ttec_scraper import scrape_outages
from .calendar.calendar_util import create_event, save_ics_file
from .email.email_util import send_email_with_attachment
from .email.email_format_util import format_events_as_html, format_criteria_table

logger = setup_logging("service-outage-monitor")

def load_config(path="config/config.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_for_provider(provider: dict):
    provider_id = provider["id"]
    title       = provider["title"]
    url         = provider["url"]
    area_kws    = provider.get("area_keywords", [])
    loc_kws     = provider.get("location_keywords", [])
    inactive_kw = provider.get("status_inactive_keyword", "CANCELLED")

    recipients  = recipients_for_provider(provider_id)
    logger.info(f"Starting to scrape {url} (provider_id={provider_id}, recipients={len(recipients)})")

    # scrape
    outages = scrape_outages(url, area_kws, loc_kws, inactive_kw)

    # build events
    events = []
    for o in outages:
        ev = create_event(
            date=o['date'],
            time=o['time'],
            title=title,
            status=o['status'],
            location=o['location'],
            description=o['description'],
            logger=logger
        )
        if ev:
            events.append(ev)

    if not events:
        logger.info(f"No matching outages for provider {provider_id}. No email/ICS.")
        return None

    # save ICS: one per provider per run date
    ics_filename = f"/root/projects/logs/{provider_id}_{datetime.now().strftime('%Y%m%d')}.ics"
    save_ics_file(events, ics_filename, logger=logger)

    # email body
    table_html = format_events_as_html(events)
    criteria_html = format_criteria_table([(title, url, area_kws, loc_kws)])

    subject = f"{title} Outages Report ({len(events)}) — {provider_id}"
    body_html = (
        "<p>Dear User,</p>"
        "<p>Please find below the scheduled outage details:</p>"
        f"{table_html}"
        "<br/>"
        f"{criteria_html}"
        "<p>Best regards,<br/>Service Outage Monitor</p>"
    )

    # send to this provider's list
    send_email_with_attachment(subject, body_html, attachment_path=ics_filename, recipients=recipients, logger=logger)
    return {"provider_id": provider_id, "ics": ics_filename, "recipients": recipients, "events": len(events)}

def main():
    cfg = load_config()
    providers = cfg.get("websites", [])

    results = []
    for p in providers:
        res = run_for_provider(p)
        if res:
            results.append(res)

    if not results:
        logger.info("Run complete: no providers produced events.")

if __name__ == "__main__":
    main()
