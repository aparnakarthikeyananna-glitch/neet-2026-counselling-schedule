import json
import re
import urllib.request
import io
import pypdf

CONFIG_FILE = "config.json"
OUTPUT_FILE = "schedule.json"

DEFAULT_STAGES = [
    {"key": "reg", "stage": "Registration & Fee", "mccDate": "05 Aug – 15 Aug", "mccTime": "Upto 02:00 PM (Pay till 5 PM)", "tnDate": "06 Aug – 14 Aug", "tnTime": "Upto 05:00 PM"},
    {"key": "choice", "stage": "Choice Filling & Locking", "mccDate": "06 Aug – 17 Aug", "mccTime": "Lock: 17 Aug (10 AM – 6 PM)", "tnDate": "15 Aug – 18 Aug", "tnTime": "Locking on 18 Aug"},
    {"key": "process", "stage": "Seat Processing", "mccDate": "18 Aug", "mccTime": "1 Day", "tnDate": "19 Aug – 20 Aug", "tnTime": "2 Days"},
    {"key": "result", "stage": "Result Publication", "mccDate": "19 Aug", "mccTime": "Provisional List", "tnDate": "21 Aug", "tnTime": "Provisional List"},
    {"key": "joining", "stage": "College Joining", "mccDate": "20 Aug – 25 Aug", "mccTime": "Verify by 26 Aug", "tnDate": "23 Aug – 27 Aug", "tnTime": "Upto 05:00 PM"}
]

MONTHS = r'(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'

def fetch_pdf_text(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n".join([page.extract_text() or "" for page in reader.pages])
    except Exception as e:
        print(f"Warning: Failed to fetch {url}: {e}")
        return ""

def extract_valid_dates(text):
    if not text:
        return []
    
    # Strict regex requiring real month names: e.g. "5th August to 15th August, 2026"
    pattern = rf'(\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS}(?:\s*,?\s*\d{{4}})?(?:\s+to\s+|\s*–\s*|\s*-\s*)\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS}(?:\s*,?\s*\d{{4}})?)'
    matches = re.findall(pattern, text, re.IGNORECASE)
    
    # Clean matches (remove extra commas/spaces)
    cleaned = []
    for m in matches:
        clean_str = re.sub(r'\s+', ' ', m).strip()
        # Normalise 'to' to '–'
        clean_str = re.sub(r'\s+to\s+', ' – ', clean_str, flags=re.IGNORECASE)
        cleaned.append(clean_str)
    return cleaned

def run():
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    
    mcc_text = fetch_pdf_text(config.get("mcc_url", ""))
    tn_text = fetch_pdf_text(config.get("tn_url", ""))

    mcc_dates = extract_valid_dates(mcc_text)
    tn_dates = extract_valid_dates(tn_text)

    output = {
        "title": config.get("title", "NEET UG 2026"),
        "round": config.get("round", "Round 1"),
        "last_updated": "Auto-synced from notice PDFs",
        "rows": DEFAULT_STAGES
    }

    # Only replace if a valid date range containing month names was parsed
    if len(mcc_dates) >= 1:
        output["rows"][0]["mccDate"] = mcc_dates[0]
    if len(tn_dates) >= 1:
        output["rows"][0]["tnDate"] = tn_dates[0]

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"Parsed MCC Dates: {mcc_dates}")
    print(f"Parsed TN Dates: {tn_dates}")
    print(f"Updated {OUTPUT_FILE} successfully.")

if __name__ == "__main__":
    run()
