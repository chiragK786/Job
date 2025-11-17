#!/usr/bin/env python3
"""
send_job_applications.py

Simple script per your request:
- Extract emails from a PDF (excluding configured domains),
- Save extracted emails to a timestamped CSV,
- Send plain+HTML email (HTML is bold+italic) with resume attached,
- After attempting sends, delete both the original PDF and the generated CSV.

Important:
- Credentials are embedded because you asked; hard-coding is insecure.
- Script will NOT delete files if SMTP login fails or if no emails are found.
"""

import re
import csv
import os
import sys
import time
import mimetypes
import pdfplumber
from datetime import date
import smtplib
from email.message import EmailMessage
from typing import Set

# ---------------------- CONFIGURATION ----------------------
# Input PDF (set your path)
PDF_PATH = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/NCR_Noida_Delhi_Gurgaon (29).pdf"

# Resume attachment (set your path)
ATTACHMENT_PATH = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/SARITA KUMARI CV1.pdf"

# Exclusions
EXCLUDED_DOMAINS = ['@squareboat.com']   # case-insensitive
ALWAYS_EXCLUDE = "info@jobcurator.in"

# EMAIL CREDENTIALS (hard-coded as requested). Gmail app-password often displayed with spaces;
# we strip spaces automatically below.
EMAIL_ADDRESS = "saritac0111@gmail.com"
EMAIL_PASSWORD = "stdo mcad mfzr ayyj"

# Email subject and bodies (includes the "Skills & Tools" section you asked for)
EMAIL_SUBJECT = "[Job Application] Application for Senior QA Engineer Role"

PLAIN_BODY = """Dear Hiring Team,

I came across that your team is hiring for a QA Engineer role. I would like to express my interest in the same. Please find my profile details below:

• Current Role: Manual & Automation Test Engineer
• Total Experience: 8 years
• Relevant Experience in QA: 5+ years
• Current Location: New Delhi
• Notice Period: Immediate Joiner

Skills & Tools:

Manual Testing, Functional Testing, Regression Testing

Automation Testing using Selenium WebDriver with Java

Test Frameworks: TestNG, Maven, Page Object Model (POM)

API Testing using Postman & Rest Assured 

Bug Tracking & Collaboration Tools: Jira, Confluence

Mobile Testing using Android Studio & BrowserStack

Interception & debugging tools: Charles Proxy

Database: MySQL 

Certifications: Manual & Automation Testing (Selenium with Java)

Attached is my updated resume for your review.
Please consider my profile for relevant openings and do let me know if any more details are required.

Thanks & Regards,
Sarita Kumari
7200979238
"""

HTML_BODY = """<html>
  <body>
    <strong><em>
      <p>Dear Hiring Team,</p>

      <p>I came across that your team is hiring for a QA Engineer role. I would like to express my interest in the same. Please find my profile details below:</p>

      <ul>
        <li>Current Role: Manual &amp; Automation Test Engineer</li>
        <li>Total Experience: 8 years</li>
        <li>Relevant Experience in QA: 5+ years</li>
        <li>Current Location: New Delhi</li>
        <li>Notice Period: Immediate Joiner</li>
      </ul>

      <p><strong>Skills &amp; Tools:</strong></p>
      <ul>
        <li>Manual Testing, Functional Testing, Regression Testing</li>
        <li>Automation Testing using Selenium WebDriver with Java</li>
        <li>Test Frameworks: TestNG, Maven, Page Object Model (POM)</li>
        <li>API Testing using Postman &amp; Rest Assured</li>
        <li>Bug Tracking &amp; Collaboration Tools: Jira, Confluence</li>
        <li>Mobile Testing using Android Studio &amp; BrowserStack</li>
        <li>Interception &amp; debugging tools: Charles Proxy</li>
        <li>Database: MySQL</li>
        <li>Certifications: Manual &amp; Automation Testing (Selenium with Java)</li>
      </ul>

      <p>Attached is my updated resume for your review.<br>
      Please consider my profile for relevant openings and do let me know if any more details are required.</p>

      <p>Thanks &amp; Regards,<br/>Sarita Kumari<br/>7200979238</p>
    </em></strong>
  </body>
</html>
"""

# Rate limit between emails (seconds)
SECONDS_BETWEEN_EMAILS = 1.0
# -----------------------------------------------------------

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b')


def get_output_csv_name(pdf_path: str) -> str:
    base = os.path.basename(pdf_path)
    first_word = re.split(r'[_ ]', base)[0]
    return f"{first_word}_{date.today().isoformat()}.csv"


def extract_emails_from_pdf(pdf_path: str) -> Set[str]:
    emails: Set[str] = set()
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for m in EMAIL_REGEX.findall(text):
                    e = m.strip().lower()
                    if e == ALWAYS_EXCLUDE:
                        continue
                    if any(e.endswith(dom.lower()) for dom in EXCLUDED_DOMAINS):
                        continue
                    emails.add(e)
    except Exception as e:
        print(f"❌ Error reading PDF '{pdf_path}': {e}")
        raise
    return emails


def write_emails_to_csv(emails: Set[str], csv_path: str):
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Email"])
            for e in sorted(emails):
                writer.writerow([e])
    except Exception as e:
        print(f"❌ Failed to write CSV '{csv_path}': {e}")
        raise


def build_message(from_addr: str, to_addr: str, subject: str, plain: str, html: str, attachment_path: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")

    if not os.path.isfile(attachment_path):
        raise FileNotFoundError(f"Attachment not found: {attachment_path}")

    ctype, _ = mimetypes.guess_type(attachment_path)
    ctype = ctype or "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)
    with open(attachment_path, "rb") as af:
        msg.add_attachment(af.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(attachment_path))

    return msg


def main():
    # Basic validations
    if not os.path.isfile(PDF_PATH):
        print(f"❌ PDF not found: {PDF_PATH}")
        sys.exit(1)
    if not os.path.isfile(ATTACHMENT_PATH):
        print(f"❌ Attachment not found: {ATTACHMENT_PATH}")
        sys.exit(1)

    # Extract emails
    emails = extract_emails_from_pdf(PDF_PATH)
    if not emails:
        print("⚠️ No emails found in the PDF. Nothing to send. Exiting without deleting files.")
        return

    # Write CSV
    csv_name = get_output_csv_name(PDF_PATH)
    write_emails_to_csv(emails, csv_name)
    print(f"✅ Extracted {len(emails)} emails -> {csv_name}")

    # Prepare credentials (strip spaces from app-password if any)
    passwd = EMAIL_PASSWORD.replace(" ", "")

    # Connect to SMTP and login
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60)
        server.login(EMAIL_ADDRESS, passwd)
        print("✅ SMTP login successful.")
    except Exception as e:
        print(f"❌ SMTP login failed: {e}")
        # Don't delete files if login fails; user can fix creds and re-run
        sys.exit(1)

    # Send emails
    sent_count = 0
    try:
        for idx, recipient in enumerate(sorted(emails), start=1):
            try:
                msg = build_message(EMAIL_ADDRESS, recipient, EMAIL_SUBJECT, PLAIN_BODY, HTML_BODY, ATTACHMENT_PATH)
                server.send_message(msg)
                sent_count += 1
                print(f"✅ [{sent_count}] Sent to: {recipient}")
            except Exception as send_err:
                print(f"❌ Failed to send to {recipient}: {send_err}")
            time.sleep(SECONDS_BETWEEN_EMAILS)
    finally:
        try:
            server.quit()
        except Exception:
            pass

    # After attempting sends, delete both the original PDF and the generated CSV
    deleted_any = False
    for p in (PDF_PATH, csv_name):
        try:
            if os.path.exists(p):
                os.remove(p)
                print(f"🗑️ Deleted: {p}")
                deleted_any = True
        except Exception as e:
            print(f"⚠️ Could not delete {p}: {e}")

    print(f"Done. Emails attempted: {len(emails)}, Successfully sent (attempted without exception): {sent_count}.")
    if not deleted_any:
        print("Note: No files were deleted (maybe missing permissions).")
    return


if __name__ == "__main__":
    main()