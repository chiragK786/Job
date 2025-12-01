import pdfplumber
import csv
import re

PDF_PATH = "/Users/chiragkhanduja/Downloads/TestingJobs_FullList (6).pdf"   # Your PDF
CSV_PATH = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/sent_emails.csv"

def extract_emails_from_pdf(pdf_path):
    emails = set()
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            found = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}", text)
            for e in found:
                emails.add(e.lower().strip())
    return emails

def extract_emails_from_csv(csv_path):
    emails = set()
    try:
        with open(csv_path, newline='') as f:
            for row in csv.reader(f):
                if row:
                    emails.add(row[0].lower().strip())
    except FileNotFoundError:
        pass
    return emails

pdf_emails = extract_emails_from_pdf(PDF_PATH)
csv_emails = extract_emails_from_csv(CSV_PATH)

only_in_pdf = pdf_emails - csv_emails
only_in_csv = csv_emails - pdf_emails
common = pdf_emails & csv_emails

print("\n🟩 Emails only in PDF (NEW emails):")
for e in sorted(only_in_pdf):
    print(" ", e)

print("\n🟦 Emails only in CSV (OLD or junk emails):")
for e in sorted(only_in_csv):
    print(" ", e)

print("\n🟨 Emails in BOTH (already sent):")
for e in sorted(common):
    print(" ", e)

print("\n📊 SUMMARY:")
print("PDF emails:", len(pdf_emails))
print("CSV emails:", len(csv_emails))
print("New emails to send:", len(only_in_pdf))
print("Common emails:", len(common))
