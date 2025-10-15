#!/usr/bin/env python3
# runner.py
from __future__ import annotations

import os
import sys
import time
import signal
import logging
import threading
import pathlib
from datetime import datetime
from zoneinfo import ZoneInfo

# --- paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# --- internal imports ---
from src.utils.my_logging import setup_logging
from src.utils.env_util import recipients_for_provider
from src.scraping.ttec_scraper import scrape_outages
from src.ics_generator.calendar_util import create_event, save_ics_file
from src.mailer.email_util import send_email_with_attachment
from src.mailer.email_format_util import format_events_as_html, format_criteria_table
from src.main import load_config

# --- APScheduler ---
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

TT_TZ = ZoneInfo("America/Port_of_Spain")

def now_tt() -> datetime:
    return datetime.now(TT_TZ)

def fmt_ts(dt: datetime) -> str:
    return dt.astimezone(TT_TZ).strftime("%Y-%m-%d %H:%M:%S")

def human_dur(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h: return f"{h}h {m}m {s}s"
    if m: return f"{m}m {s}s"
    return f"{s}s"

# --- optional phone bridge (non-blocking) ---
try:
    from notify.termux_bridge import toast, notify, wrap_notify, BridgeHandler
    _BRIDGE = True
except Exception:
    _BRIDGE = False
    def toast(*a, **k): pass
    def notify(*a, **k): pass
    def wrap_notify(*a, **k):
        def _inner(fn): return fn
        return _inner
    class BridgeHandler(logging.Handler):
        def emit(self, record): pass

# --- logging ---
logger = setup_logging("service-outage-monitor")

# Guarantee stdout handler so tmux -> runner.out receives logs
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(sh)

# Add bridge handler (ERROR+) if available
if _BRIDGE:
    bh = BridgeHandler(job_title="Outage Monitor")
    bh.setLevel(logging.ERROR)
    logger.addHandler(bh)

# --- heartbeat for boot watchdog ---
APP_ROOT = pathlib.Path(__file__).resolve().parent
RUN_LOG_DIR = APP_ROOT / "logs" / "outage-runner"
RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)
HB_FILE = RUN_LOG_DIR / "runner.heartbeat"

def _heartbeat_loop():
    while True:
        try:
            HB_FILE.write_text(str(int(time.time())))
        except Exception as e:
            logger.warning("Heartbeat write failed: %s", e)
        time.sleep(10)

threading.Thread(target=_heartbeat_loop, daemon=True).start()

# ---------------- core job ----------------
def _run_provider_impl(provider: dict):
    t_start = now_tt()
    provider_id = provider.get("id")
    title = provider["title"]
    url = provider["url"]
    area_keywords = provider.get("area_keywords", [])
    location_keywords = provider.get("location_keywords", [])
    status_inactive_keyword = provider.get("status_inactive_keyword", "CANCELLED")

    recipients = recipients_for_provider(provider_id) if provider_id else []
    if not recipients:
        logger.error(f"[{title}] No recipients for provider_id={provider_id}. Skipping email.")
        notify(f"{title}", f"⚠️ No recipients • start {fmt_ts(t_start)}", "default")
    else:
        logger.info(f"[{title}] recipients={len(recipients)}")

    logger.info(f"[{title}] Starting scrape {url}")
    toast(f"[{title}] started @ {t_start.strftime('%H:%M:%S')}")

    outages = scrape_outages(url, area_keywords, location_keywords, status_inactive_keyword)

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
            ev["date_str"] = o["date"]
            ev["status"] = o["status"]
            events.append(ev)

    if not events:
        t_end = now_tt()
        dur = human_dur((t_end - t_start).total_seconds())
        logger.info(f"[{title}] No matching outages; skipping email.")
        notify(f"{title}", f"ℹ️ No events • {fmt_ts(t_start)} → {fmt_ts(t_end)} • {dur}", "low")
        return

    ics_name = f"service_outage_{title.lower().replace(' ','_')}_{now_tt().strftime('%Y%m%d')}.ics"
    ics_path = os.path.expanduser(f"./logs/{ics_name}")
    save_ics_file(events, ics_path, logger=logger)

    table_html = format_events_as_html(events)
    crit_html = format_criteria_table([(title, url, area_keywords, location_keywords)])
    subject = f"{title} — Scheduled Outages ({len(events)})"
    body_html = (
        "<p>Dear User,</p>"
        "<p>Please find below the scheduled outage details:</p>"
        f"{table_html}<br/>{crit_html}"
        "<p>Best regards,<br/>Service Outage Monitor</p>"
    )

    send_email_with_attachment(
        subject=subject,
        body_html=body_html,
        attachment_path=ics_path,
        recipients=recipients,
        logger=logger
    )

    t_end = now_tt()
    dur = human_dur((t_end - t_start).total_seconds())
    notify(
        f"{title}",
        f"✅ Emailed {len(events)} event(s) to {len(recipients) or 0} • {fmt_ts(t_start)} → {fmt_ts(t_end)} • {dur}",
        "high"
    )

def run_provider(provider: dict):
    t0 = time.time()
    try:
        return _run_provider_impl(provider)
    except Exception as e:
        dt = time.time() - t0
        title = provider.get("title", "Provider")
        notify(title, f"❌ {type(e).__name__} • {human_dur(dt)}", "max", sticky=True)
        raise

# ---------------- scheduling ----------------
def _schedule_from_yaml(sched, cfg: dict):
    providers = cfg.get("websites", [])
    for idx, p in enumerate(providers, 1):
        cron_expr = p.get("schedule")
        title = p.get("title", f"provider{idx}")
        if not cron_expr:
            logger.warning(f"[{title}] missing 'schedule' in config.yaml — skipping")
            continue

        try:
            trigger = CronTrigger.from_crontab(cron_expr, timezone=TT_TZ)
        except Exception as e:
            logger.error(f"[{title}] invalid cron '{cron_expr}': {e}")
            toast(f"[{title}] invalid cron")
            continue

        job_id = f"provider_{idx}_{title.lower().replace(' ','_')}"
        sched.add_job(
            run_provider,
            trigger=trigger,
            id=job_id,
            kwargs={"provider": p},
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60*30,
            replace_existing=True,
        )

        now = now_tt()
        next_fire = trigger.get_next_fire_time(previous_fire_time=None, now=now)
        logger.info(f"[{title}] scheduled '{cron_expr}' as '{job_id}' (next={next_fire})")
        if next_fire:
            toast(f"[{title}] next @ {next_fire.astimezone(TT_TZ).strftime('%Y-%m-%d %H:%M')}")

def main():
    print("[runner] main() entered", flush=True)
    notify("Outage Monitor", "main() entered", "low")

    cfg = load_config()
    scheduler = BackgroundScheduler(timezone=TT_TZ)
    _schedule_from_yaml(scheduler, cfg)
    scheduler.start()
    print("[runner] APScheduler started", flush=True)
    jobs = scheduler.get_jobs()
    logger.info("APScheduler started. Press Ctrl+C to exit. jobs=%d", len(jobs))
    notify("Outage Monitor", f"Scheduler started • {len(jobs)} job(s) • {fmt_ts(now_tt())}", "low")

    def _shutdown(signum, frame):
        logger.info("Shutting down scheduler...")
        toast("Outage Monitor: shutting down…")
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
        notify("Outage Monitor", f"❌ Runner crashed: {type(e).__name__}", "max", sticky=True)
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
            notify("Outage Monitor", f"⚠️ No provider id={args.run_now}", "default")
            sys.exit(1)
        toast(f"Running {p.get('title','provider')} now…")
        run_provider(p)
        sys.exit(0)

    main()
