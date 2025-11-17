#!/usr/bin/env python3
"""
Simple script in the same single-file style you provided.
- Put the CSV (with header "Email" or single column) and the resume file paths below.
- Set EMAIL_ADDRESS and EMAIL_PASSWORD at top (visible in the file as requested).
- The script sends to unique emails not already in sent_emails.csv, appends sent addresses,
  logs daily counts in email_log.csv, and deletes the input CSV at the end.
"""

import os
import csv
import mimetypes
import smtplib
from datetime import datetime, date
from email.message import EmailMessage

import pandas as pd

# --- CONFIGURATION (edit these) ---
csv_path = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/emails.csv"  # path to input CSV
attachment_path = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Chirag_Khanduja_Sr_QA_SDET_AI_Resume_Latest.pdf"

# Visible credentials (edit these)
EMAIL_ADDRESS = "your_sender_email@example.com"
EMAIL_PASSWORD = "your_email_password_or_app_password"

# Exclusions
excluded_domains = ['@squareboat.com', '@hudle.in', '@infosys.com', '@cgi.com','@rayosys.com','@cognizant.com']
excluded_exact = {'info@jobcurator.in'}

# Sidecar files (placed next to input CSV)
base_dir = os.path.dirname(os.path.abspath(csv_path)) or os.getcwd()
sent_emails_file = os.path.join(base_dir, "sent_emails.csv")
log_file = os.path.join(base_dir, "email_log.csv")

# Email content
EMAIL_SUBJECT = "[Job Application] Application for Senior QA Engineer Role"
EMAIL_BODY = """\
Dear Hiring Manager,

I am thrilled to submit my application for the Senior QA Engineer role. With more than 3 years of experience in quality assurance and software testing, I have honed my skills in both manual and automated testing methodologies.

My proficiency encompasses tools like Selenium, Robot Framework, Postman, TestNG, Locust (for load testing), and JIRA. I possess practical experience in test planning, execution, automation of regression and API tests, and effective defect management within agile settings. In my past positions, my contributions have significantly enhanced product quality, expanded automation coverage, and ensured dependable, scalable releases.

I am confident that my technical expertise and process-oriented mindset can bring value to your QA team. Please find my resume attached for your review, and I am open to further discussions at your convenience.

Thank you for your time and consideration.

Sincerely,
Chirag Khanduja
9034226868
"""

# --- Sanity checks ---
if not os.path.isfile(csv_path):
    raise FileNotFoundError(f"Input CSV not found: {csv_path}")
if not os.path.isfile(attachment_path):
    raise FileNotFoundError(f"Attachment not found: {attachment_path}")
if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
    raise ValueError("Set EMAIL_ADDRESS and EMAIL_PASSWORD at the top of the script.")

# --- Load emails from CSV ---
df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
# Determine email column (prefer header 'Email', else first column)
email_col = None
for col in df.columns:
    if str(col).strip().lower() == "email":
        email_col = col
        break
if email_col is None:
    if len(df.columns) == 1:
        email_col = df.columns[0]
    else:
        # pick first column that contains '@' in sample values
        for col in df.columns:
            sample = df[col].astype(str).dropna().head(10).tolist()
            if any("@" in s for s in sample):
                email_col = col
                break
if email_col is None:
    raise ValueError("Could not determine email column. Ensure CSV has 'Email' header or single column of emails.")

emails = set(df[email_col].astype(str).str.strip().str.lower().replace('', pd.NA).dropna().tolist())
print(f"✅ Unique emails loaded from CSV: {len(emails)}")

# --- Filter exclusions ---
filtered = set()
for e in emails:
    if not e or '@' not in e:
        continue
    if e in excluded_exact:
        continue
    if any(e.endswith(dom) for dom in excluded_domains):
        continue
    filtered.add(e)
print(f"✅ Emails after exclusions: {len(filtered)}")

# --- Load already-sent ---
sent_emails = set()
if os.path.exists(sent_emails_file):
    with open(sent_emails_file, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                sent_emails.add(row[0].strip().lower())
print(f"ℹ️ Already sent (in sent_emails.csv): {len(sent_emails)}")

# --- Prepare send list ---
emails_to_send = sorted([e for e in filtered if e not in sent_emails])
print(f"➡️ Queued to send: {len(emails_to_send)}")

if not emails_to_send:
    print("Nothing to send. Exiting.")
    # delete CSV if you still want (kept for safety)
    try:
        os.remove(csv_path)
        print(f"🗑️ Deleted CSV file: '{csv_path}'")
    except Exception:
        pass
    raise SystemExit(0)

# --- Prepare attachment mime ---
mime_type, _ = mimetypes.guess_type(attachment_path)
mime_type = mime_type or "application/octet-stream"
maintype, subtype = mime_type.split("/", 1)

# --- SMTP connect and send ---
server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

emails_sent = 0
for idx, recipient in enumerate(emails_to_send, start=1):
    msg = EmailMessage()
    msg['Subject'] = EMAIL_SUBJECT
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = recipient
    msg.set_content(EMAIL_BODY)
    msg['X-Job-Label'] = 'Job Application'

    with open(attachment_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(attachment_path))

    try:
        server.send_message(msg)
        print(f"[{idx}/{len(emails_to_send)}] ✅ Email sent to {recipient}")
        emails_sent += 1
        # append immediately
        with open(sent_emails_file, "a", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([recipient])
    except Exception as e:
        print(f"[{idx}/{len(emails_to_send)}] ❌ Failed to send to {recipient}: {e}")

server.quit()
print(f"\n📅 Total emails actually sent in this run: {emails_sent}")

# --- Update daily log ---
today = date.today().strftime("%Y-%m-%d")
if os.path.exists(log_file):
    with open(log_file, "r", newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
else:
    rows = [["Date", "EmailsSent"]]

found = False
for i in range(1, len(rows)):
    if rows[i] and rows[i][0] == today:
        prev = int(rows[i][1]) if len(rows[i]) > 1 and rows[i][1].isdigit() else 0
        rows[i][1] = str(prev + emails_sent)
        found = True
        break
if not found:
    rows.append([today, str(emails_sent)])

with open(log_file, "w", newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerows(rows)

print(f"📅 Logged {emails_sent} sent emails for {today} into '{log_file}'")

# --- Delete input CSV ---
try:
    os.remove(csv_path)
    print(f"🗑️ Deleted CSV file: '{csv_path}'")
except Exception as e:
    print(f"⚠️ Could not delete CSV file: {e}")