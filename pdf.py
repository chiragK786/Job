import re
import csv
import pdfplumber
import os
from datetime import date

# --- Configuration ---
pdf_path = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Bangalore_Chennai (17).pdf"
excluded_domains = ['@squareboat.com', '@hudle.in','@infosys.com']
emails = set()

# --- Generate Dynamic CSV Filename ---
base_filename = os.path.basename(pdf_path)
first_word = re.split(r'[_ ]', base_filename)[0]
today_date_str = date.today().strftime("%Y-%m-%d")
output_csv_name = f"{first_word}_{today_date_str}.csv"

# --- PDF Processing ---
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b', text)
            for email in matches:
                email_lower = email.lower()
                if (
                    email_lower != "info@jobcurator.in"
                    and not any(email_lower.endswith(domain) for domain in excluded_domains)
                ):
                    emails.add(email_lower)

# --- Write to CSV ---
with open(output_csv_name, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Email"])
    for email in sorted(emails):
        writer.writerow([email])

print(f"✅ Successfully extracted {len(emails)} emails and saved to '{output_csv_name}'")

# --- Delete the PDF file ---
try:
    os.remove(pdf_path)
    print(f"🗑️ Deleted PDF file: '{pdf_path}'")
except Exception as e:
    print(f"⚠️ Could not delete PDF file: {e}")