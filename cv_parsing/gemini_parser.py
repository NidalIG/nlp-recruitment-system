import time
import google.generativeai as genai
from cv_parsing.models import CandidateInfo

# Configuration API
genai.configure(api_key="AIzaSyB143FEjb5OZixvJ21XwnyQPYTls7rth1A")

PROMPT_TEMPLATE = """Extract the information from the given text extracted from a candidate CV and return a JSON object:
{'name':'','email':'','phone':'','skills':'','education':'','experience':'','certifications':'','languages':''}

Extraction rules:
name – full name of the candidate
email – valid email address
phone – phone number
skills – max 15, no duplicates
education – degree, institution, year
experience – job title, company, years, description
certifications – list
languages – list

Mandatory requirements:
- Ensure each record contains all 8 fields
- If field is missing, return "N/A"
- Output must be valid JSON ONLY

Below is the given text extracted:
PDF_TEXT
"""

model = genai.GenerativeModel("gemini-2.5-flash")

def parse_cv_with_gemini(cv_text: str) -> dict:
    result = model.generate_content(
        PROMPT_TEMPLATE.replace("PDF_TEXT", cv_text),
        generation_config=genai.GenerationConfig(
            temperature=0.7,
            response_mime_type="application/json",
            response_schema=CandidateInfo
        ),
    )
    time.sleep(5)
    return result.text
