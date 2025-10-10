# 🛰️ Service Outage Monitor

Automated utility outage monitor that: - Scrapes utility/ISP outage
pages on a schedule. - Filters results by **area/location keywords**. -
Generates a `.ics` calendar file. - Emails a nicely formatted HTML
summary + ICS attachment to configured recipients.

Supports multiple providers via `config/config.yaml`, each with its own
scrape keywords, schedule, and recipient list (defined in `.env`).

------------------------------------------------------------------------

## 📁 Folder Structure

    service-outage-monitor/
    ├─ src/
    │  ├─ main.py                  # Manual single-run entrypoint
    │  ├─ scraping/                # Page scrapers
    │  │  └─ ttec_scraper.py
    │  ├─ ics_generator/           # ICS calendar creation utilities
    │  │  └─ calendar_util.py
    │  ├─ mailer/                  # Email utilities
    │  │  ├─ email_util.py
    │  │  └─ email_format_util.py
    │  ├─ utils/
    │  │  ├─ my_logging.py
    │  │  └─ env_util.py
    │  └─ __init__.py
    ├─ config/
    │  └─ config.yaml              # Provider list, URLs, schedules, and keywords
    ├─ .env.example                # Example environment config
    ├─ runner.py                   # APScheduler-based continuous runner
    ├─ requirements.txt
    ├─ README.md
    ├─ LICENSE
    └─ logs/                       # Run + email logs and generated ICS files

------------------------------------------------------------------------

## ⚙️ Setup

### 1. Clone and install dependencies
- cd to your preferred installation location
``` bash
git clone https://github.com/yourname/service-outage-monitor.git
cd service-outage-monitor
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure your environment

Copy and edit your `.env` file:

``` bash
cp .env.example .env
```

Set:

``` dotenv
# SMTP settings
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=your-app-password
TIMEZONE=America/Port_of_Spain

# Global fallback recipients (optional)
TO_EMAILS=you@gmail.com

# Per-provider lists
RECIPIENTS__ttec_north_east=you@gmail.com,other@example.com
RECIPIENTS__ttec_east_only=alerts@example.com
```

> 💡 Gmail requires an **App Password** (see your Google Account →
> Security → App Passwords).

------------------------------------------------------------------------

## 🧩 Configuration (`config/config.yaml`)

Each provider defines: - `id`: unique slug used in `.env` - `title`:
display name - `url`: page to scrape - `area_keywords` /
`location_keywords`: filters - `status_inactive_keyword`: optional
cancellation keyword - `schedule`: **cron expression** for when
APScheduler should run it

Example:

``` yaml
websites:
  - id: "ttec_north_east"
    title: "TTEC"
    url: "https://ttec.co.tt/cis/outages_public.html"
    area_keywords: ["north", "east"]
    location_keywords: ["Fredrick", "Maravel", "Fernandez"]
    status_inactive_keyword: "CANCELLED"
    schedule: "0 6 * * mon,wed"

  - id: "ttec_east_only"
    title: "TTEC"
    url: "https://ttec.co.tt/cis/outages_public.html"
    area_keywords: ["east", "north"]
    location_keywords: ["Eastern Main", "Foster"]
    status_inactive_keyword: "CANCELLED"
    schedule: "5 13 * * mon,wed,fri"
```

------------------------------------------------------------------------

## 🚀 Running the App

### ▶ Manual one-time run

Run all providers immediately (useful for testing):

``` bash
python src/main.py
```

Run a single provider immediately:

``` bash
python src/runner.py --run-now ttec_east_only
```

------------------------------------------------------------------------

### 🕒 Continuous Scheduler Mode

Start the background scheduler to run jobs per their YAML cron
expressions:

``` bash
python src/runner.py
```

You'll see logs like:

    [TTEC] scheduled with cron '5 13 * * mon,wed,fri' as job 'provider_2_ttec' (next_run=2025-10-10 13:05:00-04:00)
    APScheduler started. Press Ctrl+C to exit.

Each run will scrape, generate the `.ics`, and email results.

------------------------------------------------------------------------

### 🔁 Automatic restart (Termux/Ubuntu)

Use the included `scripts/start_runner.sh`:

``` bash
bash scripts/start_runner.sh
```

It will: - Keep the runner alive in a loop. - Write logs under
`~/projects/logs/outage-runner/`. - Auto-restart if it crashes or the
phone restarts (via Termux:Boot or cron).

------------------------------------------------------------------------

## 📬 Email Output

Each run sends a formatted HTML email with: - Table of outages - Search
criteria summary - `.ics` calendar attachment for direct import

If **no outages are found**, no email is sent.

------------------------------------------------------------------------

## 🧠 Tips

-   You can schedule **multiple days and times** using standard cron
    syntax (e.g. `0,30 8 * * 1,3`).
-   To modify intervals or times, just update `config.yaml` and
    **restart the runner**.
-   Logs and `.ics` files are stored under `~/projects/logs/`.

------------------------------------------------------------------------

## 🧰 Future Enhancements

-   Add GUI or web dashboard for editing schedules.
-   OCR for channing social image post for updates

------------------------------------------------------------------------

## 🔐 Security Notes

-   Keep `.env` and your SMTP credentials private.\
-   Use App Passwords or tokens --- **never your raw email password**.\
-   This tool does not store or send sensitive personal data.

------------------------------------------------------------------------

## 🧾 License

MIT License © 2025\
Author: Skitzofrenzy
