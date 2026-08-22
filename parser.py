import json
import urllib.request
import io
import pypdf
import os
import google.generativeai as genai

CONFIG_FILE = "config.json"
OUTPUT_FILE = "schedule.json"

# Configure Gemini API
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("Warning: GEMINI_API_KEY environment variable not set.")
genai.configure(api_key=API_KEY)

DEFAULT_STAGES = [
    {"key": "reg", "stage": "Registration & Fee", "mccDate": "", "mccTime": "", "tnDate": "", "tnTime": ""},
    {"key": "choice", "stage": "Choice Filling & Locking", "mccDate": "", "mccTime": "", "tnDate": "", "tnTime": ""},
    {"key": "process", "stage": "Seat Processing", "mccDate": "", "mccTime": "", "tnDate": "", "tnTime": ""},
    {"key": "result", "stage": "Result Publication", "mccDate": "", "mccTime": "", "tnDate": "", "tnTime": ""},
    {"key": "joining", "stage": "College Joining", "mccDate": "", "mccTime": "", "tnDate": "", "tnTime": ""}
]

def fetch_pdf_text(url):
    if not url:
        return ""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
            reader = pypdf.PdfReader(io.BytesIO(content))
            return "\n".join([page.extract_text() or "" for page in reader.pages])
    except Exception as e:
        print(f"Warning: Failed to fetch {url}: {e}")
        return ""

def extract_dates_with_ai(text, authority):
    if not text.strip():
        return {}

    prompt = f"""
    You are a schedule extraction assistant. Extract the {authority} NEET UG counselling schedule dates and times from the text below.
    Map the findings to these exact 5 stages. If a stage isn't mentioned, leave the date and time strings empty.
    
    1. "reg": Registration, Payment, or Fee Submission
    2. "choice": Choice Filling and Locking
    3. "process": Seat Processing / Processing of seat allotment
    4. "result": Result Publication / Allotment result
    5. "joining": College Joining / Reporting to allotted institute

    Return ONLY a valid JSON object (no markdown, no backticks) with this structure:
    {{
      "reg": {{"date": "extracted date range", "time": "extracted time limits"}},
      "choice": {{"date": "...", "time": "..."}},
      "process": {{"date": "...", "time": "..."}},
      "result": {{"date": "...", "time": "..."}},
      "joining": {{"date": "...", "time": "..."}}
    }}

    Text:
    {text}
    """

    try:
        # Use gemini-1.5-flash as it is fast, cheap, and excellent at parsing text to JSON
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Clean up response in case the model adds markdown code blocks
        result_text = response.text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:-3].strip()
        elif result_text.startswith("```"):
            result_text = result_text[3:-3].strip()
            
        return json.loads(result_text)
    except Exception as e:
        print(f"AI Extraction failed for {authority}: {e}")
        return {}

def run():
    # Load config (fallback to dummy config for testing if file missing)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    else:
        config = {
            "mcc_url": "https://cdnbbsr.s3waas.gov.in/s3e0f7a4d0ef9b84b83b693bbf3feb8e6e/uploads/2026/08/202608191403764226.pdf",
            "tn_url": "https://tnmedicalselection.net/news/19082026233844.pdf",
            "title": "NEET UG 2026",
            "round": "Round 1"
        }

    print("Fetching PDF texts...")
    mcc_text = fetch_pdf_text(config.get("mcc_url", ""))
    tn_text = fetch_pdf_text(config.get("tn_url", ""))

    print("Extracting schedules via AI...")
    mcc_schedule = extract_dates_with_ai(mcc_text, "MCC (All India Quota)")
    tn_schedule = extract_dates_with_ai(tn_text, "Tamil Nadu State Quota")

    output = {
        "title": config.get("title", "NEET UG 2026"),
        "round": config.get("round", "Round 1"),
        "last_updated": "Auto-synced via AI extraction",
        "rows": []
    }

    # Merge AI results into the unified structure
    for stage_template in DEFAULT_STAGES:
        stage_key = stage_template["key"]
        
        # Pull MCC data
        if stage_key in mcc_schedule:
            stage_template["mccDate"] = mcc_schedule[stage_key].get("date", "")
            stage_template["mccTime"] = mcc_schedule[stage_key].get("time", "")
            
        # Pull TN data
        if stage_key in tn_schedule:
            stage_template["tnDate"] = tn_schedule[stage_key].get("date", "")
            stage_template["tnTime"] = tn_schedule[stage_key].get("time", "")
            
        output["rows"].append(stage_template)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"Updated {OUTPUT_FILE} successfully.")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    run()
