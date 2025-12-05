#!/usr/bin/env python3

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

# ---------------------- CONFIG ----------------------

PDF_PATH = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/NCR_Noida_Delhi_Gurgaon (45).pdf"
ATTACHMENT_PATH = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/ChetnaBansal_Resume_.pdf"

EXCLUDED_DOMAINS = ["@squareboat.com"]
ALWAYS_EXCLUDE = "info@jobcurator.in"

EMAIL_ADDRESS = "chetnabansal.rohini@gmail.com"
EMAIL_PASSWORD = "kmbm oseh vajy jkhe"

# DEFAULT = plain
EMAIL_MODE = "html"   # change to "html" anytime

EMAIL_SUBJECT = "Your perfect candidate for content marketing is here"

# File that stores already sent emails
SENT_FILE = "chetna_mail_sent.txt"

PLAIN_BODY = """Hola,

I am writing because I am actively looking for my next opportunity to create impactful and conversion-focused content in the tech space, and I was curious if your team is currently hiring for a content or copywriting role.

If so, here is a quick snapshot of what I'd bring:

I’m Chetna, a technical content writer with 1 year 10 months of experience specifically in B2B SaaS and software development. I specialize in simplifying complex tech topics for business audiences and crafting copy that drives action.

My portfolio is enclosed in the attachment that showcases samples of how I turn technical details into compelling narratives.

Are you open to a brief conversation to explore if there is a potential fit? I’d be grateful for the opportunity.

Looking forward,
Chetna
"""

HTML_BODY = """<html>
  <body>

    <p>Hola,</p>

    <p>
      I am writing because I am actively looking for my next opportunity to create 
      impactful and <b>conversion-focused content</b> in the tech space, and I was curious 
      if your team is currently hiring for a content or <b>copywriting</b> role.
    </p>

    <p>If so, here is a quick snapshot of what I'd bring:</p>

    <p>
      I’m Chetna, a <b>technical content writer</b> with 1 year 10 months of experience 
      specifically in <b>B2B SaaS</b> and <b>software development</b>.  
      I specialize in <b>simplifying complex tech topics</b> for <b>business audiences</b> 
      and crafting copy that drives action.
    </p>

    <p>
      My portfolio is enclosed in the attachment that showcases samples of how I turn 
      technical details into <b>compelling narratives</b>.
    </p>

    <p>
      Are you open to a brief conversation to explore if there is a potential fit?  
      I’d be grateful for the opportunity.
    </p>

    <p>Looking forward,<br>Chetna</p>

  </body>
</html>
"""

SECONDS_BETWEEN_EMAILS = 1.0

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b")


# ---------------------- HELPERS ----------------------

def get_output_csv_name(pdf_path: str) -> str:
    base = os.path.basename(pdf_path)
    first_word = re.split(r"[_ ]", base)[0]
    return f"{first_word}_{date.today().isoformat()}.csv"


def extract_emails_from_pdf(pdf_path: str) -> Set[str]:
    emails = set()
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for m in EMAIL_REGEX.findall(text):
                e = m.strip().lower()
                if e == ALWAYS_EXCLUDE:
                    continue
                if any(e.endswith(dom) for dom in EXCLUDED_DOMAINS):
                    continue
                emails.add(e)
    return emails


def write_emails_to_csv(emails: Set[str], csv_path: str):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Email"])
        for e in sorted(emails):
            writer.writerow([e])


def load_sent_emails() -> Set[str]:
    if not os.path.exists(SENT_FILE):
        return set()
    with open(SENT_FILE, "r", encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}


def save_sent_email(email: str):
    with open(SENT_FILE, "a", encoding="utf-8") as f:
        f.write(email + "\n")


# ---------------------- EMAIL BUILDER ----------------------

def build_message(from_addr, to_addr, subject, plain, html, attachment_path, mode):
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject

    if mode.lower() == "plain":
        msg.set_content(plain)
    else:
        msg.set_content(plain)
        msg.add_alternative(html, subtype="html")

    ctype, _ = mimetypes.guess_type(attachment_path)
    ctype = ctype or "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)

    with open(attachment_path, "rb") as af:
        msg.add_attachment(
            af.read(),
            maintype=maintype,
            subtype=subtype,
            filename=os.path.basename(attachment_path),
        )

    return msg


# ---------------------- MAIN ----------------------

def main():

    if not os.path.isfile(PDF_PATH):
        print(f"❌ PDF not found: {PDF_PATH}")
        sys.exit(1)

    if not os.path.isfile(ATTACHMENT_PATH):
        print(f"❌ Attachment not found: {ATTACHMENT_PATH}")
        sys.exit(1)

    # Load previous sent emails
    already_sent = load_sent_emails()
    print(f"📌 Already sent: {len(already_sent)} emails tracked.")

    # Extract new emails
    emails = extract_emails_from_pdf(PDF_PATH)

    # Filter out emails already sent before
    emails_to_send = [e for e in emails if e not in already_sent]

    print(f"📩 Found {len(emails)} emails in PDF.")
    print(f"➡ Sending only {len(emails_to_send)} new emails (skipping already contacted).")

    if not emails_to_send:
        print("⚠️ No new emails to send. Exiting safely.")
        return

    csv_name = get_output_csv_name(PDF_PATH)
    write_emails_to_csv(set(emails_to_send), csv_name)

    passwd = EMAIL_PASSWORD.replace(" ", "")

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(EMAIL_ADDRESS, passwd)
        print("✅ SMTP login successful.")
    except Exception as e:
        print(f"❌ SMTP login failed: {e}")
        sys.exit(1)

    sent_count = 0

    try:
        for recipient in emails_to_send:
            try:
                msg = build_message(
                    EMAIL_ADDRESS,
                    recipient,
                    EMAIL_SUBJECT,
                    PLAIN_BODY,
                    HTML_BODY,
                    ATTACHMENT_PATH,
                    EMAIL_MODE,
                )
                server.send_message(msg)
                sent_count += 1
                print(f"✅ Sent to: {recipient}")

                # Save to sent-file so next time script won't re-send
                save_sent_email(recipient)

            except Exception as err:
                print(f"❌ Failed sending to {recipient}: {err}")

            time.sleep(SECONDS_BETWEEN_EMAILS)

    finally:
        server.quit()

    # Delete PDF + CSV
    for p in (PDF_PATH, csv_name):
        if os.path.exists(p):
            try:
                os.remove(p)
                print(f"🗑️ Deleted: {p}")
            except:
                pass

    print(f"\n🎉 DONE — Sent: {sent_count} new emails.\n")


if __name__ == "__main__":
    main()
