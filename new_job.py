import re
import csv
import pdfplumber
import os
from datetime import date, datetime
import pandas as pd
import smtplib
from email.message import EmailMessage
import mimetypes

# --- CONFIGURATION ---
pdf_path = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Pune Mumbai (16).pdf"
excluded_domains = ['@squareboat.com', '@hudle.in', '@infosys.com']
emails = set()

# --- DYNAMIC CSV FILENAME ---
base_filename = os.path.basename(pdf_path)
first_word = re.split(r'[_ ]', base_filename)[0]
today_date_str = date.today().strftime("%Y-%m-%d")
output_csv_name = f"{first_word}_{today_date_str}.csv"

# --- PDF PROCESSING ---
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

# --- WRITE TO CSV ---
with open(output_csv_name, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Email"])
    for email in sorted(emails):
        writer.writerow([email])

print(f"✅ Successfully extracted {len(emails)} emails and saved to '{output_csv_name}'")

# --- DELETE PDF ---
try:
    os.remove(pdf_path)
    print(f"🗑️ Deleted PDF file: '{pdf_path}'")
except Exception as e:
    print(f"⚠️ Could not delete PDF file: {e}")

# ================== EMAIL SENDING ==================

# Gmail credentials
EMAIL_ADDRESS = 'chiragkhanduja786@gmail.com'
EMAIL_PASSWORD = 'ibbe sacy xfxu olfe'  # App Password

# Attachment file (resume)
attachment_path = '/Users/chiragkhanduja/PycharmProjects/PythonProject11/Chirag_Khanduja_Sr_QA_SDET_AI_Resume_Latest.pdf'
if not os.path.isfile(attachment_path):
    raise FileNotFoundError(f"Attachment not found: {attachment_path}")

# Email body
email_body = """\
Dear Hiring Manager,

I am thrilled to submit my application for the Senior QA Engineer role. With more than 3 years of experience in quality assurance and software testing, I have honed my skills in both manual and automated testing methodologies.

My proficiency encompasses tools like Selenium, Robot Framework, Postman, TestNG, Locust (for load testing), and JIRA. I possess practical experience in test planning, execution, automation of regression and API tests, and effective defect management within agile settings. In my past positions, my contributions have significantly enhanced product quality, expanded automation coverage, and ensured dependable, scalable releases.

I am confident that my technical expertise and process-oriented mindset can bring value to your QA team. Please find my resume attached for your review, and I am open to further discussions at your convenience.

Thank you for your time and consideration.

Sincerely,
Chirag Khanduja
9034226868
"""

# Read generated CSV for emails
data = pd.read_csv(output_csv_name)

# Setup SMTP server
server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

emails_sent = 0

for index, row in data.iterrows():
    msg = EmailMessage()
    msg['Subject'] = '[Job Application] Application for Senior QA Engineer Role'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = row['Email']
    msg.set_content(email_body)
    msg['X-Job-Label'] = 'Job Application'

    mime_type, _ = mimetypes.guess_type(attachment_path)
    mime_type = mime_type or 'application/octet-stream'
    maintype, subtype = mime_type.split('/')

    with open(attachment_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(attachment_path))

    try:
        server.send_message(msg)
        print(f"✅ Email sent to {row['Email']}")
        emails_sent += 1
    except Exception as e:
        print(f"❌ Failed to send email to {row['Email']}: {e}")

server.quit()

# === LOG EMAIL COUNT DATE-WISE ===
log_file = '/Users/chiragkhanduja/PycharmProjects/PythonProject11/email_log.csv'
today = datetime.now().strftime("%Y-%m-%d")

if os.path.exists(log_file):
    with open(log_file, "r", newline="") as f:
        reader = list(csv.reader(f))

    found = False
    for i in range(1, len(reader)):
        if reader[i][0] == today:
            current_count = int(reader[i][1])
            reader[i][1] = str(current_count + emails_sent)
            found = True
            break

    if not found:
        reader.append([today, str(emails_sent)])

    with open(log_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(reader)

else:
    with open(log_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "EmailsSent"])
        writer.writerow([today, emails_sent])

print(f"\n📅 Total emails sent today ({today}): {emails_sent} — logged in email_log.csv")

# --- DELETE CSV FILE ---
try:
    os.remove(output_csv_name)
    print(f"🗑️ Deleted CSV file: '{output_csv_name}'")
except Exception as e:
    print(f"⚠️ Could not delete CSV file: {e}")