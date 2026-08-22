import json
import urllib.request
import io
import pdfplumber
import os
from google import genai

CONFIG_FILE = "config.json"
OUTPUT_FILE = "schedule.json"

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
        
        extracted_content = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                # 1. Extract tabular data and format it cleanly for the LLM
                tables = page.extract_tables()
                for table in tables:
                    extracted_content.append("--- Structured Table Data ---")
                    for row in table:
                        # Clean newlines inside cells and separate columns with pipes
                        clean_row = [str(cell).replace('\n', ' ').strip() if cell else "BLANK" for cell in row]
                        extracted_content.append(" | ".join(clean_row))
                    extracted_content.append("-----------------------------")
                
                # 2. Extract regular unstructured text 
                # layout=True helps preserve basic visual spacing in paragraphs
                text = page.extract_text(layout=True)
                if text:
                    extracted_content.append("--- Unstructured Text ---")
                    extracted_content.append(text)

        return "\n".join(extracted_content)
    except Exception as e:
        print(f"Warning: Failed to fetch {url}: {e}")
        return ""

def extract_dates_with_ai(text, authority, client):
    if not text.strip():
        return {}

    prompt = f"""
    You are a schedule extraction assistant. Extract the {authority} NEET UG counselling schedule dates and times from the text below.
    Important: The text may contain tabular data (columns separated by '|') or unstructured paragraphs.
    Only extract the dates relevant specifically to {authority}.
    
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
        response = client.models.generate_content(
            model='gemini-2.5-flash', # Updated to a valid SDK model string
            contents=prompt
        )
        
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
    try:
        client = genai.Client()
    except Exception as e:
        print(f"Failed to initialize Gemini Client: {e}")
        return

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    else:
        config = {
            "mcc_url": "https://cdnbbsr.s3waas.gov.in/s3e0f7a4d0ef9b84b83b693bbf3feb8e6e/uploads/2026/08/202608191403764226.pdf",
            "tn_url": "", 
            "title": "NEET UG 2026",
            "round": "Round 1"
        }

    print("Fetching PDF texts...")
    mcc_text = fetch_pdf_text(config.get("mcc_url", ""))
    tn_text = fetch_pdf_text(config.get("tn_url", ""))

    print("Extracting schedules via AI...")
    mcc_schedule = extract_dates_with_ai(mcc_text, "All India Quota", client)
    tn_schedule = extract_dates_with_ai(tn_text, "Tamil Nadu State Quota", client) if tn_text else {}

    output = {
        "title": config.get("title", "NEET UG 2026"),
        "round": config.get("round", "Round 1"),
        "last_updated": "Auto-synced via AI extraction",
        "rows": []
    }

    for stage_template in DEFAULT_STAGES:
        stage_key = stage_template["key"]
        
        if stage_key in mcc_schedule:
            stage_template["mccDate"] = mcc_schedule[stage_key].get("date", "")
            stage_template["mccTime"] = mcc_schedule[stage_key].get("time", "")
            
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
