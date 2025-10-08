from datetime import datetime
import requests
import yaml
import my_logging as logging  # Make sure this points to your custom log_util.py
from bs4 import BeautifulSoup
from my_logging import setup_logging
from calendar_util import create_event, save_ics_file

# Setup logging for the Service Outage Monitor app
logger = setup_logging("service-outage-monitor")

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
    return " ".join(t.split())

def scrape_outages(url, area_keywords, location_keywords, status_inactive_keyword):
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    rows = soup.find_all("tr", class_="MsoNormalTable")
    
    filtered_outages = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 4:
            date = norm_text(cols[0].get_text())
            area = norm_text(cols[1].get_text())
            location = norm_text(cols[2].get_text())
            time = norm_text(cols[3].get_text())

            # Check if the location starts with "CANCELLED"
            status = "Active"  # Default status
            if location.lower().startswith(status_inactive_keyword.lower()):
                status = "Cancelled"
            
            # Description should be the text from the Location column (third column)
            description = location  # Use location as description
            # logging.debug(f"Description: {description}")

            # Filter by Area and Location
            if any(area_kw.lower() in area.lower() for area_kw in area_keywords) and \
               any(loc_kw.lower() in location.lower() for loc_kw in location_keywords):
                filtered_outages.append({
                    "date": date,
                    "area": area,
                    "location": location,
                    "time": time,
                    "status": status,  # Add status to the log entry
                    "description": description  # Add description
                })
    return filtered_outages

def main():
    config = load_config()  # Load config
    providers = config.get("websites", [])
    
    all_events = []
    
    for provider in providers:
        url = provider['url']
        area_keywords = provider.get('area_keywords', [])
        location_keywords = provider.get('location_keywords', [])
        status_inactive_keyword = provider['status_inactive_keyword']
        title = provider['title']
        
        # Scrape data
        outages = scrape_outages(url, area_keywords, location_keywords, status_inactive_keyword)
        
        # Log something
        logger.info(f"Starting to scrape {url}")

        # Process the events and create ICS file
        for outage in outages:
            event = create_event(
                date=outage['date'],
                time=outage['time'],
                title=title,
                status=outage['status'],
                location=outage['location'],
                description=outage['description'],
                logger=logger  # Pass logger to the event creation function
            )
            if event:
                all_events.append(event)

    if all_events:
        # Save ICS file
        filename = f"/root/projects/logs/service_outage_monitor_{datetime.now().strftime('%Y%m%d')}.ics"
        save_ics_file(all_events, filename, logger=logger)  # Pass logger to save function
    else:
        logger.info("No matching outages found. No ICS file generated.")
        
if __name__ == "__main__":
    main()
