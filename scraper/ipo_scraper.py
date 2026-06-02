"""
scraper/ipo_scraper.py
Scrapes IPO data from Chittorgarh. Falls back to built-in sample data
if network is unavailable. Python 3.8 compatible - no type hints.
"""

import os
import time
import logging
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://www.chittorgarh.com/report/ipo-subscription-status-live-data-allotment/93/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
RAW_DATA_PATH = os.getenv("RAW_DATA_PATH", "/opt/airflow/data/raw")

SAMPLE_DATA = [
    {"ipo_name": "Tata Technologies",        "open_date": "22-Nov-2023", "close_date": "24-Nov-2023", "listing_date": "30-Nov-2023", "issue_size": 3043.00, "offer_price": 500,  "list_price": 1200, "current_price": 980,  "qib": 203.41, "hni": 62.11,  "rii": 36.10,  "total_subscription": 69.43,  "sector": "Technology",      "exchange": "NSE"},
    {"ipo_name": "IREDA",                    "open_date": "21-Nov-2023", "close_date": "23-Nov-2023", "listing_date": "29-Nov-2023", "issue_size": 2150.21, "offer_price": 32,   "list_price": 50,   "current_price": 220,  "qib": 26.04,  "hni": 31.19,  "rii": 25.07,  "total_subscription": 38.80,  "sector": "Finance",         "exchange": "NSE"},
    {"ipo_name": "Mankind Pharma",           "open_date": "25-Apr-2023", "close_date": "27-Apr-2023", "listing_date": "09-May-2023", "issue_size": 4326.35, "offer_price": 1080, "list_price": 1300, "current_price": 2100, "qib": 26.61,  "hni": 17.38,  "rii": 14.42,  "total_subscription": 41.62,  "sector": "Pharma",          "exchange": "NSE"},
    {"ipo_name": "Nexus Select Trust",       "open_date": "09-May-2023", "close_date": "11-May-2023", "listing_date": "19-May-2023", "issue_size": 3200.00, "offer_price": 100,  "list_price": 96,   "current_price": 130,  "qib": 5.02,   "hni": 3.14,   "rii": 1.87,   "total_subscription": 6.17,   "sector": "Real Estate",     "exchange": "NSE"},
    {"ipo_name": "Zaggle Prepaid",           "open_date": "14-Sep-2023", "close_date": "18-Sep-2023", "listing_date": "22-Sep-2023", "issue_size": 563.56,  "offer_price": 164,  "list_price": 155,  "current_price": 143,  "qib": 45.22,  "hni": 37.80,  "rii": 40.12,  "total_subscription": 70.30,  "sector": "Technology",      "exchange": "NSE"},
    {"ipo_name": "Concord Biotech",          "open_date": "04-Aug-2023", "close_date": "07-Aug-2023", "listing_date": "18-Aug-2023", "issue_size": 1551.00, "offer_price": 706,  "list_price": 900,  "current_price": 1640, "qib": 174.25, "hni": 166.06, "rii": 91.70,  "total_subscription": 24.93,  "sector": "Pharma",          "exchange": "NSE"},
    {"ipo_name": "EMS",                      "open_date": "19-Oct-2023", "close_date": "23-Oct-2023", "listing_date": "26-Oct-2023", "issue_size": 321.00,  "offer_price": 211,  "list_price": 320,  "current_price": 410,  "qib": 178.05, "hni": 263.17, "rii": 121.18, "total_subscription": 157.00, "sector": "Infrastructure",  "exchange": "NSE"},
    {"ipo_name": "Global Health Medanta",    "open_date": "03-Nov-2022", "close_date": "07-Nov-2022", "listing_date": "16-Nov-2022", "issue_size": 2205.57, "offer_price": 336,  "list_price": 401,  "current_price": 870,  "qib": 36.53,  "hni": 45.22,  "rii": 28.00,  "total_subscription": 52.00,  "sector": "Healthcare",      "exchange": "NSE"},
    {"ipo_name": "Archean Chemical",         "open_date": "09-Nov-2022", "close_date": "11-Nov-2022", "listing_date": "21-Nov-2022", "issue_size": 1462.32, "offer_price": 407,  "list_price": 497,  "current_price": 620,  "qib": 55.10,  "hni": 102.30, "rii": 40.50,  "total_subscription": 68.00,  "sector": "Chemicals",       "exchange": "NSE"},
    {"ipo_name": "Five Star Business",       "open_date": "09-Nov-2022", "close_date": "11-Nov-2022", "listing_date": "21-Nov-2022", "issue_size": 1960.00, "offer_price": 474,  "list_price": 400,  "current_price": 780,  "qib": 13.20,  "hni": 11.40,  "rii": 9.80,   "total_subscription": 18.00,  "sector": "Finance",         "exchange": "NSE"},
    {"ipo_name": "Bikaji Foods",             "open_date": "03-Nov-2022", "close_date": "07-Nov-2022", "listing_date": "16-Nov-2022", "issue_size": 881.22,  "offer_price": 300,  "list_price": 322,  "current_price": 420,  "qib": 93.20,  "hni": 73.50,  "rii": 32.40,  "total_subscription": 26.66,  "sector": "FMCG",            "exchange": "NSE"},
    {"ipo_name": "DCX Systems",              "open_date": "31-Oct-2022", "close_date": "02-Nov-2022", "listing_date": "11-Nov-2022", "issue_size": 500.56,  "offer_price": 207,  "list_price": 280,  "current_price": 390,  "qib": 119.40, "hni": 166.00, "rii": 81.20,  "total_subscription": 145.00, "sector": "Defence",         "exchange": "NSE"},
    {"ipo_name": "Harsha Engineers",         "open_date": "14-Sep-2022", "close_date": "16-Sep-2022", "listing_date": "26-Sep-2022", "issue_size": 755.00,  "offer_price": 330,  "list_price": 450,  "current_price": 470,  "qib": 165.52, "hni": 225.49, "rii": 177.47, "total_subscription": 74.70,  "sector": "Auto Ancillaries","exchange": "NSE"},
    {"ipo_name": "Delhivery",                "open_date": "11-May-2022", "close_date": "13-May-2022", "listing_date": "24-May-2022", "issue_size": 5235.00, "offer_price": 487,  "list_price": 493,  "current_price": 390,  "qib": 1.89,   "hni": 0.42,   "rii": 1.07,   "total_subscription": 1.63,   "sector": "Logistics",       "exchange": "NSE"},
    {"ipo_name": "LIC",                      "open_date": "04-May-2022", "close_date": "09-May-2022", "listing_date": "17-May-2022", "issue_size": 21008.48,"offer_price": 949,  "list_price": 867,  "current_price": 770,  "qib": 2.83,   "hni": 2.91,   "rii": 1.99,   "total_subscription": 2.95,   "sector": "Finance",         "exchange": "NSE"},
    {"ipo_name": "Rainbow Children Medicare","open_date": "27-Apr-2022", "close_date": "29-Apr-2022", "listing_date": "10-May-2022", "issue_size": 1580.77, "offer_price": 542,  "list_price": 633,  "current_price": 730,  "qib": 79.90,  "hni": 108.22, "rii": 57.30,  "total_subscription": 92.00,  "sector": "Healthcare",      "exchange": "NSE"},
    {"ipo_name": "Campus Activewear",        "open_date": "26-Apr-2022", "close_date": "28-Apr-2022", "listing_date": "09-May-2022", "issue_size": 1400.00, "offer_price": 292,  "list_price": 380,  "current_price": 260,  "qib": 22.01,  "hni": 10.80,  "rii": 14.20,  "total_subscription": 51.75,  "sector": "Retail",          "exchange": "NSE"},
    {"ipo_name": "Manoj Vaibhav Gems",       "open_date": "13-Sep-2023", "close_date": "15-Sep-2023", "listing_date": "20-Sep-2023", "issue_size": 270.44,  "offer_price": 215,  "list_price": 221,  "current_price": 190,  "qib": None,   "hni": None,   "rii": None,   "total_subscription": None,   "sector": "Jewellery",       "exchange": "NSE"},
    {"ipo_name": "Droneacharya Aerial",      "open_date": "21-Dec-2022", "close_date": "23-Dec-2022", "listing_date": "29-Dec-2022", "issue_size": 34.00,   "offer_price": 54,   "list_price": 53,   "current_price": 63,   "qib": None,   "hni": None,   "rii": None,   "total_subscription": None,   "sector": "Technology",      "exchange": "NSE"},
    {"ipo_name": "Paradeep Phosphates",      "open_date": "17-May-2022", "close_date": "19-May-2022", "listing_date": "26-May-2022", "issue_size": 1501.73, "offer_price": 42,   "list_price": 43,   "current_price": 70,   "qib": None,   "hni": None,   "rii": None,   "total_subscription": None,   "sector": "Chemicals",       "exchange": "NSE"},
]


def fetch_page(url, retries=3, delay=5):
    for attempt in range(1, retries + 1):
        try:
            logger.info("Fetching %s (attempt %d)", url, attempt)
            response = requests.get(url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except Exception as exc:
            logger.warning("Attempt %d failed: %s", attempt, exc)
            if attempt < retries:
                time.sleep(delay)
    logger.warning("All fetch attempts failed — using fallback sample data.")
    return None


def parse_ipo_table(soup):
    records = []
    table = soup.find("table", {"class": lambda c: c and "table" in c})
    if not table:
        logger.warning("No table found on page.")
        return records
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    logger.info("Columns found: %s", headers)
    for row in table.find("tbody").find_all("tr"):
        cells = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cells) == len(headers):
            records.append(dict(zip(headers, cells)))
    logger.info("Parsed %d rows from table.", len(records))
    return records


def clean_numeric(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if str(value).strip() in ["-", "N/A", "nan", ""]:
        return None
    cleaned = str(value).replace("\u20b9", "").replace(",", "").replace("%", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalize_records(raw_records):
    normalized = []
    for rec in raw_records:
        normalized.append({
            "ipo_name":           rec.get("IPO Name",       rec.get("Company",       rec.get("ipo_name", ""))),
            "open_date":          rec.get("Open Date",      rec.get("Open",          rec.get("open_date", ""))),
            "close_date":         rec.get("Close Date",     rec.get("Close",         rec.get("close_date", ""))),
            "listing_date":       rec.get("Listing Date",   rec.get("Listing",       rec.get("listing_date", ""))),
            "issue_size":         clean_numeric(rec.get("Issue Size (Cr.)", rec.get("Issue Size", rec.get("issue_size")))),
            "offer_price":        clean_numeric(rec.get("Offer Price",  rec.get("Price",         rec.get("offer_price")))),
            "list_price":         clean_numeric(rec.get("List Price",   rec.get("Listing Price", rec.get("list_price")))),
            "current_price":      clean_numeric(rec.get("Current Price",                         rec.get("current_price"))),
            "qib":                clean_numeric(rec.get("QIB",  rec.get("qib"))),
            "hni":                clean_numeric(rec.get("HNI",  rec.get("hni"))),
            "rii":                clean_numeric(rec.get("RII",  rec.get("rii"))),
            "total_subscription": clean_numeric(rec.get("Total", rec.get("Subscription", rec.get("total_subscription")))),
            "sector":             rec.get("Sector",   rec.get("sector",   "")),
            "exchange":           rec.get("Exchange", rec.get("exchange", "NSE")),
        })
    return pd.DataFrame(normalized)


def get_fallback_df():
    logger.info("Using fallback sample data (%d records).", len(SAMPLE_DATA))
    return pd.DataFrame(SAMPLE_DATA)


def save_raw(df):
    os.makedirs(RAW_DATA_PATH, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(RAW_DATA_PATH, "ipo_raw_%s.csv" % timestamp)
    df.to_csv(filepath, index=False)
    logger.info("Raw data saved -> %s  (%d records)", filepath, len(df))
    return filepath


def run_scraper():
    logger.info("=== IPO Scraper Started ===")
    soup = fetch_page(BASE_URL)
    if soup is not None:
        raw_records = parse_ipo_table(soup)
        df = normalize_records(raw_records) if raw_records else get_fallback_df()
    else:
        df = get_fallback_df()
    filepath = save_raw(df)
    logger.info("=== IPO Scraper Completed ===")
    return filepath


if __name__ == "__main__":
    run_scraper()
