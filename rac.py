import re
import csv
import pdfplumber
import os
from datetime import date
import smtplib
from email.message import EmailMessage
import mimetypes

# --- Configuration ---
pdf_path = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/NCR_Noida_Delhi_Gurgaon (41).pdf"
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

# --- Send the CSV as an Email Attachment ---
# Change these to your credentials and recipient  # Use Gmail App Password (not your regular password)
EMAIL_ADDRESS = 'chiragkhanduja786@gmail.com'
EMAIL_PASSWORD = 'lnyo jrcb niia ksha'
RECIPIENT_EMAIL = 'jyotsnasingh855@gmail.com'

subject = "HR email"
body = "Please find attached the extracted email list CSV."

# Prepare the email
msg = EmailMessage()
msg['Subject'] = subject
msg['From'] = EMAIL_ADDRESS
msg['To'] = RECIPIENT_EMAIL
msg.set_content(body)

# Attach the CSV
mime_type, _ = mimetypes.guess_type(output_csv_name)
mime_type = mime_type or 'application/octet-stream'
maintype, subtype = mime_type.split('/')

with open(output_csv_name, 'rb') as f:
    msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=output_csv_name)

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    print(f"📧 CSV sent to {RECIPIENT_EMAIL} successfully.")
    # Delete the CSV after sending
    try:
        os.remove(output_csv_name)
        print(f"🗑️ Deleted CSV file: '{output_csv_name}'")
    except Exception as e:
        print(f"⚠️ Could not delete CSV file: {e}")
except Exception as e:
    print(f"❌ Failed to send email: {e}")