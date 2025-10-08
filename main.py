import requests
import yaml
import my_logging as logging  # Make sure this points to your custom log_util.py
from bs4 import BeautifulSoup
from my_logging import setup_logging

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
            
            # Filter by Area and Location
            if any(area_kw.lower() in area.lower() for area_kw in area_keywords) and \
               any(loc_kw.lower() in location.lower() for loc_kw in location_keywords):
                filtered_outages.append({
                    "date": date,
                    "area": area,
                    "location": location,
                    "time": time,
                    "status": status  # Add status to the log entry
                })
    return filtered_outages


def main():
    config = load_config()  # Load config
    providers = config.get("websites", [])
    
    for provider in providers:
        url = provider['url']
        area_keywords = provider.get('area_keywords', [])
        location_keywords = provider.get('location_keywords', [])
        status_inactive_keyword = provider['status_inactive_keyword']
        
        # Scrape data
        outages = scrape_outages(url, area_keywords, location_keywords, status_inactive_keyword)
        
        # Log something
        logger.info(f"Starting to scrape {url}")

        # Log the results
        if outages:
            logger.info(f"Found {len(outages)} outages for {url}")
            for outage in outages:
                logger.info(f"Status: {outage['status']}, Date: {outage['date']}, Time: {outage['time']}, Area: {outage['area']}, Location: {outage['location']}")
        else:
            logger.info(f"No matching outages found for {url}")

if __name__ == "__main__":
    main()
