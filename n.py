
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
pdf_path = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Hyderabad (24).pdf"
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
EMAIL_ADDRESS = 'neetu.74m@gmail.com'
EMAIL_PASSWORD = 'bzoa jgrh suug tcgi'  # App Password

# Attachment file (resume)
attachment_path = '/Users/chiragkhanduja/PycharmProjects/PythonProject11/1Neetu resume-1.pdf'
if not os.path.isfile(attachment_path):
    raise FileNotFoundError(f"Attachment not found: {attachment_path}")

# Email body
email_body = """\
I hope you are doing well.

My name is Neetu, and I am currently working as a Sales Manager at Kotak Life Insurance. I have over 5 years of experience in banking and financial services, with a strong focus on customer relationship management, sales growth, and business development.

I am exploring new opportunities where I can contribute my skills and experience in sales, client servicing, and financial products. I have attached my updated resume for your reference. Kindly let me know if there are any suitable openings in your organization or if you could refer my profile for the same.

I would be grateful for any consideration or guidance you can provide.

Thank you for your time and support.

Warm regards,
Neetu
📞 +91-7082273749
✉️ neetu96g@gmail.com
"""

# Read generated CSV for emails
data = pd.read_csv(output_csv_name)

# Setup SMTP server
server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

emails_sent = 0

for index, row in data.iterrows():
    msg = EmailMessage()
    msg['Subject'] = 'Inquiry Regarding Job Opportunities / Referral'
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