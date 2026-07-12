#!/usr/bin/env python3
"""
FINAL MULTI-PDF EMAIL SENDER SCRIPT
- Merges JobCurator + STS PDF
- Full Anti-Spam System
- Updated Email Body (polished professional version, includes experience line)
- Preview CSV Mode

Change: Removed the experience filter so emails are extracted from all pages.
"""

import re
import csv
import os
import time
import random
import mimetypes
import smtplib
import pdfplumber
from email.message import EmailMessage
from datetime import date
from typing import Set, List

# ---------------- CONFIG ----------------
PDF_PATHS = [
    "/Users/chiragkhanduja/PycharmProjects/PythonProject11/TestingJobs_FullList (9).pdf"  # Job Curator
                      # Software Testing Studio
]

ATTACHMENT_PATH = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Chirag_Khanduja_Sr_QA_SDET_AI_Resume_Latest.pdf"

EMAIL_ADDRESS = "chiragkhanduja786@gmail.com"
EMAIL_PASSWORD = "lnyo jrcb niia ksha"

SENT_EMAILS_FILE = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/sent_emails.csv"
LOG_FILE = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/email_log.csv"
PREVIEW_CSV = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/preview_recipients.csv"

EXCLUDED_DOMAINS = [
    '@squareboat.com', '@hudle.in', '@infosys.com',
    '@cgi.com', '@rayosys.com', '@cognizant.com'
]

# DRY RUN → Only create preview CSV
DRY_RUN = False


# ---------------- UPDATED EMAIL BODY ----------------
EMAIL_SUBJECT = "Application — QA Automation / SDET (Chirag Khanduja)"

EMAIL_BODY = """
<p>Dear Hiring Manager,</p>

<p>
I hope you’re doing well. I’m writing to express my interest in QA Automation / SDET opportunities at your organization. 
I have approximately <strong>4 years</strong> of experience in QA Automation and SDET roles, focused on building reliable
automation frameworks and improving product quality. I bring strong automation and testing experience and would welcome
the chance to contribute to your engineering team.
</p>

<p><strong>Quick highlights:</strong></p>
<ul>
  <li><strong>Experience:</strong> ~4 years in QA Automation / SDET roles (3–5 years range).</li>
  <li><strong>Automation:</strong> Playwright, Selenium, Appium, Pytest — built and maintained end-to-end frameworks.</li>
  <li><strong>API testing:</strong> REST API validation with Postman and automated integration checks.</li>
  <li><strong>Test engineering:</strong> Designed release-ready test suites, regression coverage, and CI integration.</li>
  <li><strong>Collaboration:</strong> Proven experience working closely with developers, PMs, and product teams.</li>
</ul>

<p>
Attached is my resume for your review. I’d appreciate the opportunity to discuss how I can help with your QA automation needs — 
I’m available for a brief 15-minute call at your convenience.
</p>

<p>
Thank you for your time.
</p>

<p>
Warm regards,<br>
<strong>Chirag Khanduja</strong><br>
QA Automation Engineer | SDET<br>
903-422-6868
</p>
"""


# ---------------- ANTI-SPAM CONFIG ----------------
PER_EMAIL_DELAY_MIN = 1.8
PER_EMAIL_DELAY_MAX = 4.2

DOMAIN_BURST_THRESHOLD = 3
DOMAIN_BURST_PAUSE = (10, 25)

# Note: Long cooldown removed per prior request


# ---------------- HELPERS ----------------
def load_sent_emails(file: str) -> Set[str]:
    if not os.path.exists(file):
        return set()
    try:
        with open(file, newline="") as f:
            return {row[0].lower() for row in csv.reader(f) if row}
    except:
        return set()


def append_sent(file: str, email: str):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "a", newline="") as f:
        csv.writer(f).writerow([email])


def update_log(log_path: str, count: int):
    today = date.today().strftime("%Y-%m-%d")
    rows = [["Date", "Count"]]

    if os.path.exists(log_path):
        with open(log_path, newline="") as f:
            rows = list(csv.reader(f))

    updated = False
    for r in rows[1:]:
        if r[0] == today:
            r[1] = str(int(r[1]) + count)
            updated = True

    if not updated:
        rows.append([today, str(count)])

    with open(log_path, "w", newline="") as f:
        csv.writer(f).writerows(rows)


# ---------------- RICH PROGRESS BAR ----------------
USE_RICH = True
try:
    from rich.progress import Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, TextColumn
except:
    USE_RICH = False


def rich_progress(total):
    return Progress(
        TextColumn("[bold green]Sending Emails:"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn()
    )


def simple_progress(done, total):
    bar_len = 45
    filled = int(done / total * bar_len) if total else 0
    bar = "█" * filled + "-" * (bar_len - filled)
    print(f"\r[{bar}] {done}/{total}", end="")


# ---------------- PDF EMAIL EXTRACTION ----------------
def extract_emails_from_pdfs(pdf_paths: List[str]) -> dict:
    emails = {}

    for path in pdf_paths:
        if not os.path.exists(path):
            print(f"⚠️ Missing PDF: {path}")
            continue

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""

                # No experience filter: extract emails from all pages
                found = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}", text)

                for e in found:
                    e = e.lower().strip()

                    if any(e.endswith(d) for d in EXCLUDED_DOMAINS):
                        continue
                    if e == "info@jobcurator.in":
                        continue

                    emails[e] = emails.get(e, 0) + 1

    return emails


# ---------------- MAIN ----------------
def main():
    if not os.path.exists(ATTACHMENT_PATH):
        raise FileNotFoundError(ATTACHMENT_PATH)

    all_emails = extract_emails_from_pdfs(PDF_PATHS)
    send_list = sorted(all_emails.keys())

    sent_before = load_sent_emails(SENT_EMAILS_FILE)
    send_list = [e for e in send_list if e not in sent_before]

    if not send_list:
        print("✔ No new emails found.")
        return

    # -------- DRY RUN PREVIEW --------
    if DRY_RUN:
        print(f"⚡ DRY RUN: Writing preview → {PREVIEW_CSV}")
        with open(PREVIEW_CSV, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Email", "Occurrences"])
            for e in send_list:
                writer.writerow([e, all_emails[e]])
        print("✔ Preview complete. Set DRY_RUN=False to send.")
        return

    # -------- SEND EMAILS --------
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

    mime = mimetypes.guess_type(ATTACHMENT_PATH)[0] or "application/octet-stream"
    maintype, subtype = mime.split("/")

    total = len(send_list)
    sent = 0
    domain_count = {}

    if USE_RICH:
        progress = rich_progress(total)
        progress.start()
        task = progress.add_task("send", total=total)
    else:
        print("Rich missing → using simple progress")

    for to_email in send_list:
        msg = EmailMessage()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = EMAIL_SUBJECT
        msg.add_alternative(EMAIL_BODY, subtype="html")

        with open(ATTACHMENT_PATH, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype,
                               filename=os.path.basename(ATTACHMENT_PATH))

        try:
            server.send_message(msg)
            sent += 1
            append_sent(SENT_EMAILS_FILE, to_email)
            print(f"\n✔ Sent {sent}/{total}: {to_email}")
        except Exception as e:
            print(f"\n❌ Failed: {to_email} → {e}")

        if USE_RICH:
            progress.update(task, advance=1)
        else:
            simple_progress(sent, total)

        # Domain burst pause
        domain = to_email.split("@")[1]
        domain_count[domain] = domain_count.get(domain, 0) + 1
        if domain_count[domain] % DOMAIN_BURST_THRESHOLD == 0:
            pause = random.uniform(*DOMAIN_BURST_PAUSE)
            print(f"\n⏸️ Domain burst pause for {domain}: {pause:.1f}s")
            time.sleep(pause)

        # Per email delay
        time.sleep(random.uniform(PER_EMAIL_DELAY_MIN, PER_EMAIL_DELAY_MAX))

        # Long cooldown removed by request (no additional pauses here)

    if USE_RICH:
        progress.stop()

    server.quit()

    update_log(LOG_FILE, sent)

    print(f"\n🎉 DONE — Sent {sent} emails successfully.")


if __name__ == "__main__":
    main()