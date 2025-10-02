# Outage Monitor (Weekly)
Polls utility/ISP pages for scheduled outage notices, filters by your area keywords, and emails you a calendar (.ics).

## Quick Start
1. **Clone/Copy** this folder to your server (Linux recommended).
2. Create a virtual env and install deps:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set your SMTP + timezone:
   ```bash
   cp .env.example .env
   # edit with your email/app password (Gmail requires App Passwords)
   ```
4. Edit `config.yaml`:
   - Put the real URLs for your providers.
   - Set `area_keywords` as THEY label your location on each site.
   - Tweak CSS selectors under `parsing` after inspecting each page (use your browser DevTools).
5. Test a run:
   ```bash
   python main.py
   ```
   You should get an email with `scheduled-outages-YYYYMMDD.ics` attached.

## Cron (run once a week)
Edit your crontab:
```bash
crontab -e
# Run every Monday at 8:00 AM local time
0 8 * * 1  cd /path/to/outage-monitor && /bin/bash -lc 'source .venv/bin/activate && python main.py >> run.log 2>&1'
```

## Notes & Tips
- If a site lists outages in images/PDFs or loads content dynamically, switch that provider to `parsing.mode: regex` and widen the `item_selector` or parse the full text. For heavy JS pages, consider adding Playwright.
- Date parsing uses `dateparser` with a future preference. If only a date (no time) is posted, defaults are applied from `config.yaml`.
- Events are de-duplicated by a stable UID tied to URL + start time.
- Import the `.ics` into Google Calendar/Outlook, or just click the attachment in your email app to add.
- Security: store secrets in `.env`, rotate App Passwords, and keep this repo private.

## Extending
- Add Slack/Discord notifications for found events.
- Write a small API that serves the next 14 days as JSON.
- Dockerize for easier deployment.
