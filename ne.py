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
pdf_path = "/Users/chiragkhanduja/Downloads/TestingJobs_FullList (1).pdf"
excluded_domains = ['@hudle.com']
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
EMAIL_ADDRESS = 'neetu.74m@gmail.com'
EMAIL_PASSWORD = 'bzoa jgrh suug tcgi'  # App Password

# Attachment file (resume)
attachment_path = '/Users/chiragkhanduja/PycharmProjects/PythonProject11/1Neetu resume-1.pdf'
if not os.path.isfile(attachment_path):
    raise FileNotFoundError(f"Attachment not found: {attachment_path}")

# --- EMAIL BODY (plain-text fallback, shown if client can't render HTML) ---
email_body_plain = """\
Dear Hiring Manager,

I am writing to express my interest in Sales, Relationship Management, and Business Development opportunities within the Banking, Financial Services, and FMCG sectors.

I am currently working as a Sales Manager at Kotak Life Insurance, with over 5 years of progressive experience across ICICI Bank Ltd and Kotak Mahindra Bank Ltd. My core strengths include Client Relationship Management, Sales Growth, Cross-Selling, Credit Card Acquisition, Customer Retention, and Business Development, with a consistent track record of achieving monthly sales targets and building long-term client relationships.

Key Skills: Sales & Business Development | Relationship Management | Cross-Selling & Upselling | Credit Card Sales | Customer Relationship Management (CRM) | Target Achievement | Banking Operations | Client Servicing | Team Coordination | MS Office

I have attached my updated resume for your review. I would welcome the opportunity to discuss how my experience in sales and relationship management could add value to your organization, or if you could kindly refer my profile for any suitable openings.

Thank you for your time and consideration.

Warm regards,
Neetu
Sales Manager | Banking & Financial Services
Phone: +91-7082273749
Email: neetu96g@gmail.com
"""

# --- EMAIL BODY (HTML version, with bold ATS keywords — renders in Gmail/Outlook etc.) ---
email_body_html = """\
<html>
  <body style="font-family: Calibri, Arial, sans-serif; font-size: 14px; color: #222;">
    <p>Dear Hiring Manager,</p>

    <p>I am writing to express my interest in <b>Sales, Relationship Management, and Business Development</b>
    opportunities within the <b>Banking, Financial Services, and FMCG</b> sectors.</p>

    <p>I am currently working as a <b>Sales Manager</b> at <b>Kotak Life Insurance</b>, with over
    <b>5 years of progressive experience</b> across <b>ICICI Bank Ltd</b> and <b>Kotak Mahindra Bank Ltd</b>.
    My core strengths include <b>Client Relationship Management, Sales Growth, Cross-Selling, Credit Card
    Acquisition, Customer Retention,</b> and <b>Business Development</b>, with a consistent track record of
    achieving monthly sales targets and building long-term client relationships.</p>

    <p><b>Key Skills:</b> Sales &amp; Business Development | Relationship Management | Cross-Selling &amp;
    Upselling | Credit Card Sales | Customer Relationship Management (CRM) | Target Achievement |
    Banking Operations | Client Servicing | Team Coordination | MS Office</p>

    <p>I have attached my updated resume for your review. I would welcome the opportunity to discuss how my
    experience in sales and relationship management could add value to your organization, or if you could
    kindly refer my profile for any suitable openings.</p>

    <p>Thank you for your time and consideration.</p>

    <p>Warm regards,<br>
    <b>Neetu</b><br>
    Sales Manager | Banking &amp; Financial Services<br>
    📞 +91-7082273749<br>
    ✉️ neetu96g@gmail.com</p>
  </body>
</html>
"""

# Read generated CSV for emails
data = pd.read_csv(output_csv_name)

# Setup SMTP server
server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

emails_sent = 0

for index, row in data.iterrows():
    msg = EmailMessage()
    msg['Subject'] = 'Application for Sales / Relationship Management Roles — Neetu'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = row['Email']

    # Plain text fallback + bold HTML alternative (bold only shows in HTML-capable clients)
    msg.set_content(email_body_plain)
    msg.add_alternative(email_body_html, subtype='html')

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