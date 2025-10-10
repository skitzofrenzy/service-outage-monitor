#!/usr/bin/env python3
# runner.py
from __future__ import annotations

import os, sys, time, signal
from datetime import datetime

# --- put src/ on sys.path so we can import internal packages ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# --- internal imports (NO 'src.' prefix since SRC_DIR is on sys.path) ---
from src.utils.my_logging import setup_logging
from src.utils.env_util import recipients_for_provider

from scraping.ttec_scraper import scrape_outages
from ics_generator.calendar_util import create_event, save_ics_file
from mailer.email_util import send_email_with_attachment
from mailer.email_format_util import format_events_as_html
from src.main import load_config  # reuse the repo-relative loader from src/main.py

# --- APScheduler ---
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from datetime import datetime

logger = setup_logging("service-outage-monitor")

def run_provider(provider: dict):
    """
    Single provider run: scrape -> build events -> ics -> email (per-provider list via .env).
    """
    provider_id = provider.get("id")
    title = provider["title"]
    url = provider["url"]
    area_keywords = provider.get("area_keywords", [])
    location_keywords = provider.get("location_keywords", [])
    status_inactive_keyword = provider.get("status_inactive_keyword", "CANCELLED")

   # resolve recipients for this provider id
    recipients = recipients_for_provider(provider_id) if provider_id else []
    if not recipients:
        logger.error(f"[{title}] No recipients provided for provider_id={provider_id}. Skipping email.")

    logger.info(f"[{title}] Starting scrape: {url} (provider_id={provider_id}, recipients={len(recipients)})")
    outages = scrape_outages(url, area_keywords, location_keywords, status_inactive_keyword)

    # build events list
    events = []
    for o in outages:
        ev = create_event(
            date=o["date"],
            time=o["time"],
            title=title,
            status=o["status"],
            location=o["location"],
            description=o["description"],
            logger=logger
        )
        if ev:
            # carry some extra for the email table
            ev["date_str"] = o["date"]
            ev["status"] = o["status"]
            events.append(ev)

    if not events:
        logger.info(f"[{title}] No matching outages; skipping email.")
        return

    # write provider-specific ICS
    ics_name = f"service_outage_{title.lower().replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.ics"
    ics_path = os.path.expanduser(f"~/projects/logs/{ics_name}")
    save_ics_file(events, ics_path, logger=logger)

    # build email body
    table_html = format_events_as_html(events)

    # include the criteria summary for this provider
    crit_html = (
        "<h3>Criteria used</h3>"
        '<table border="1" cellpadding="5" cellspacing="0">'
        "<thead><tr><th>Provider</th><th>URL</th><th>Area Keywords</th><th>Location Keywords</th></tr></thead>"
        "<tbody>"
        f"<tr><td>{title}</td><td><a href=\"{url}\">{url}</a></td>"
        f"<td>{', '.join(area_keywords)}</td><td>{', '.join(location_keywords)}</td></tr>"
        "</tbody></table>"
    )

    subject = f"{title} — Scheduled Outages ({len(events)})"
    body_html = (
        "<p>Dear User,</p>"
        "<p>Please find below the scheduled outage details:</p>"
        f"{table_html}<br/>{crit_html}"
        "<p>Best regards,<br/>Service Outage Monitor</p>"
    )

    # send email; email_util reads TO_EMAILS from .env (or pass recipients list here)
    send_email_with_attachment(
        subject=subject,
        body_html=body_html,
        attachment_path=ics_path,
        recipients=recipients,
        logger=logger
    )

def _schedule_from_yaml(sched, cfg: dict):
    tz = ZoneInfo("America/Port_of_Spain")
    providers = cfg.get("websites", [])
    for idx, p in enumerate(providers, 1):
        cron_expr = p.get("schedule")
        title = p.get("title", f"provider{idx}")
        if not cron_expr:
            logger.warning(f"[{title}] missing 'schedule' in config.yaml — skipping")
            continue

        try:
            trigger = CronTrigger.from_crontab(cron_expr, timezone="America/Port_of_Spain")
        except Exception as e:
            logger.error(f"[{title}] invalid cron '{cron_expr}': {e}")
            continue

        job_id = f"provider_{idx}_{title.lower().replace(' ','_')}"
        job = sched.add_job(
            run_provider,
            trigger=trigger,
            id=job_id,
            kwargs={"provider": p},
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60*30,
            replace_existing=True,
        )

        # Compute next run time via the trigger (compatible with v3/v4)
        now = datetime.now(tz)
        next_fire = trigger.get_next_fire_time(previous_fire_time=None, now=now)

        logger.info(
            f"[{title}] scheduled with cron '{cron_expr}' as job '{job_id}' "
            f"(next_run={next_fire})"
        )


def main():
    cfg = load_config()  # src/main.py resolves repo_root/config/config.yaml
    scheduler = BackgroundScheduler(timezone="America/Port_of_Spain")
    _schedule_from_yaml(scheduler, cfg)
    scheduler.start()
    logger.info("APScheduler started. Press Ctrl+C to exit.")

    # Graceful shutdown
    def _shutdown(signum, frame):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while True:
            time.sleep(60)
    except SystemExit:
        pass
    except Exception as e:
        logger.exception(f"Runner crashed: {e}")
        raise

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-now", metavar="PROVIDER_ID", help="Run one provider immediately and exit")
    args = parser.parse_args()

    if args.run_now:
        cfg = load_config()
        p = next((x for x in cfg.get("websites", []) if x.get("id") == args.run_now), None)
        if not p:
            logger.error(f"No provider with id={args.run_now}")
            sys.exit(1)
        run_provider(p)
        sys.exit(0)

    main()
