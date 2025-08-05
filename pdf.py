import re
import csv
import pdfplumber
import os  # Added for handling file paths
from datetime import date  # Added for getting the current date

# --- Configuration ---
pdf_path = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Pune Mumbai (9).pdf"
excluded_domains = ['@squareboat.com', '@hudle.in']
emails = set()

# --- Generate Dynamic CSV Filename ---
# 1. Get just the filename from the path (e.g., "NCR_Noida_Delhi_Gurgaon (7).pdf")
base_filename = os.path.basename(pdf_path)

# 2. Get the first word of the filename before the first underscore or space
first_word = re.split(r'[_ ]', base_filename)[0]

# 3. Get today's date in YYYY-MM-DD format
today_date_str = date.today().strftime("%Y-%m-%d")

# 4. Combine them to create the final CSV filename
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
# Use the dynamically generated filename here instead of a hardcoded name
with open(output_csv_name, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Email"])
    for email in sorted(emails):
        writer.writerow([email])

print(f"✅ Successfully extracted {len(emails)} emails and saved to '{output_csv_name}'")