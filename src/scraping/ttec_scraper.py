# scraping/ttec_scraper.py
from bs4 import BeautifulSoup
import requests

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

            status = "Active"
            if location.lower().startswith(status_inactive_keyword.lower()):
                status = "Cancelled"

            if any(a.lower() in area.lower() for a in area_keywords) and \
               any(l.lower() in location.lower() for l in location_keywords):
                filtered_outages.append({
                    "date": date,
                    "area": area,
                    "location": location,
                    "time": time,
                    "status": status,
                    "description": location
                })
    return filtered_outages
