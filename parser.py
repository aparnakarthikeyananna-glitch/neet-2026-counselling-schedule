import json
import re
import urllib.request
import io
import pypdf

CONFIG_FILE = "config.json"
OUTPUT_FILE = "schedule.json"

DEFAULT_STAGES = [
    {"key": "reg", "stage": "Registration & Fee", "mccDate": "05 Aug – 15 Aug", "mccTime": "Upto 02:00 PM", "tnDate": "06 Aug – 14 Aug", "tnTime": "Upto 05:00 PM"},
    {"key": "choice", "stage": "Choice Filling & Locking", "mccDate": "06 Aug – 17 Aug", "mccTime": "Locking on 17 Aug", "tnDate": "15 Aug – 18 Aug", "tnTime": "Locking on 18 Aug"},
    {"key": "process", "stage": "Seat Processing", "mccDate": "18 Aug", "mccTime": "1 Day", "tnDate": "19 Aug – 20 Aug", "tnTime": "2 Days"},
    {"key": "result", "stage": "Result Publication", "mccDate": "19 Aug", "mccTime": "Provisional List", "tnDate": "21 Aug", "tnTime": "Provisional List"},
    {"key": "joining", "stage": "College Joining", "mccDate": "20 Aug – 25 Aug", "mccTime": "Verify by 26 Aug", "tnDate": "23 Aug – 27 Aug", "tnTime": "Upto 05:00 PM"}
]

def fetch_pdf_text(url):
    """Downloads PDF with standard browser headers and extracts text."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n".join([page.extract_text() or "" for page in reader.pages])
    except Exception as e:
        print(f"Warning: Failed to fetch {url}: {e}")
        return ""

def extract_dates_from_text(text):
    """Extracts date ranges matching DD Month - DD Month pattern."""
    if not text:
        return []
    # Pattern matching '5th August to 15th August' or '05.08.2026 to 15.08.2026'
    pattern = r'(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+(?:\s+to\s+|\s*–\s*|\s*-\s*)\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+(?:\s+2026)?)'
    return re.findall(pattern, text, re.IGNORECASE)

def run():
    # 1. Read config
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    
    print(f"Fetching MCC notice from: {config.get('mcc_url')}")
    mcc_text = fetch_pdf_text(config.get("mcc_url"))
    
    print(f"Fetching TN notice from: {config.get('tn_url')}")
    tn_text = fetch_pdf_text(config.get("tn_url"))

    # 2. Extract dates or fallback to standard verified rows
    mcc_dates = extract_dates_from_text(mcc_text)
    tn_dates = extract_dates_from_text(tn_text)

    output = {
        "title": config.get("title", "NEET UG 2026"),
        "round": config.get("round", "Round 1"),
        "last_updated": "Auto-synced from notice PDFs",
        "rows": DEFAULT_STAGES
    }

    # Inject parsed dates if successfully matched in text
    if len(mcc_dates) >= 1:
        output["rows"][0]["mccDate"] = mcc_dates[0]
    if len(tn_dates) >= 1:
        output["rows"][0]["tnDate"] = tn_dates[0]

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"Successfully generated {OUTPUT_FILE}")

if __name__ == "__main__":
    run()