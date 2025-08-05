import re
import csv
import pdfplumber
import pandas as pd

# Paths
pdf_path = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/TestingJobs_FullList (1).pdf"
csv_list_path = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/email_list.csv"  # Your CSV with known emails
output_csv = "hyd.csv"

emails = set()

# Load known emails from your CSV
csv_data = pd.read_csv(csv_list_path)
csv_data.columns = [c.strip() for c in csv_data.columns]
known_emails = set(csv_data['Email'].astype(str).str.lower())

# Define excluded domains
excluded_domains = ['@squareboat.com', '@hudle.in']

# Extract and filter emails from PDF
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
                    and email_lower not in known_emails
                ):
                    emails.add(email_lower)

# Write to output CSV
with open(output_csv, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Email"])
    for email in sorted(emails):
        writer.writerow([email])

print(f"Filtered emails written to {output_csv}")
