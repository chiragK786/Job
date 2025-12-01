#!/usr/bin/env python3
"""
FINAL MULTI-PDF EMAIL SENDER SCRIPT
- Merges JobCurator + STS PDF
- Filters ONLY 3+ years / 3–5 years JDs
- Full Anti-Spam System
- Updated Email Body
- Preview CSV Mode
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
    "/Users/chiragkhanduja/Downloads/TestingJobs_FullList (6).pdf"  # Job Curator
                      # Software Testing Studio
]

ATTACHMENT_PATH = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Chirag_Khanduja_Sr_QA_SDET_AI_Resume_Latest.pdf"

EMAIL_ADDRESS = "chiragkhanduja786@gmail.com"
EMAIL_PASSWORD = "xshh zjbn ckjg yryl"

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
EMAIL_BODY = """
<p>Dear Hiring Manager,</p>

<p>
I hope you’re doing well. I’m reaching out to express my interest in any 
<b>QA Automation / SDET</b> opportunities at your organization.
</p>

<p>A quick overview of my background:</p>

<ul>
  <li><b>Automation Skills:</b> Experienced with Playwright, Selenium, Appium, Pytest.</li>
  <li><b>API Testing:</b> Strong understanding of REST APIs, Postman, and backend validation workflows.</li>
  <li><b>Framework Building:</b> Skilled in creating clean, maintainable automation frameworks from scratch.</li>
  <li><b>Quality Ownership:</b> Functional & regression testing, release readiness, and proactive issue identification.</li>
  <li><b>Team Collaboration:</b> Comfortable working closely with developers, PMs, and product teams.</li>
</ul>

<p>
I enjoy working in fast-paced engineering environments and contributing to high-quality product delivery.
I've attached my updated resume for your review, and I would truly appreciate it if you could consider my profile 
for any relevant openings you are hiring for.
</p>

<p>
Thank you so much for your time. Please feel free to reach out if you need any additional details from my side.
</p>

<p>
Warm Regards,<br>
<b>Chirag Khanduja</b><br>
<b>9034226868</b><br>
QA Automation Engineer | SDET
</p>
"""


# ---------------- ANTI-SPAM CONFIG ----------------
PER_EMAIL_DELAY_MIN = 1.8
PER_EMAIL_DELAY_MAX = 4.2

DOMAIN_BURST_THRESHOLD = 3
DOMAIN_BURST_PAUSE = (10, 25)

COOLDOWN_EVERY = 30
COOLDOWN_MIN_SECONDS = 120
COOLDOWN_MAX_SECONDS = 300


# ---------------- EXPERIENCE FILTER (ultimate) ----------------
def has_3_plus_exp(text: str) -> bool:
    if not text:
        return False

    t = text.lower()
    t = t.replace("yrs", "years").replace("yr", "year")
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    t = re.sub(r"\s*\+\s*", "+", t)
    t = re.sub(r"\s*-\s*", "-", t)
    t = re.sub(r"\s+", " ", t).strip()

    reject = [
        r"\bfresher\b",
        r"\bintern\b",
        r"\b0-?1\s*year",
        r"\b1-?2\s*year",
        r"\b2\s*years?(?!.*-)",
        r"\b6\+?\s*years?",
        r"\b7\+?\s*years?",
        r"\b8\+?\s*years?",
        r"\b9\+?\s*years?",
        r"\b10\+?\s*years?"
    ]
    for p in reject:
        if re.search(p, t):
            return False

    accept = [
        r"\b3\+?\s*years?\b",
        r"\b3-4\s*years?\b",
        r"\b3-5\s*years?\b",
        r"\b4\s*years?\b",
        r"\b5\s*years?\b",
        r"\b3\.\d+\s*years?\b"
    ]
    for p in accept:
        if re.search(p, t):
            return True

    t2 = re.sub(r"\s+", "", t)
    compact_accept = [
        r"3\+?years?",
        r"3-4years?",
        r"3-5years?",
        r"3\.\d+years?"
    ]
    for p in compact_accept:
        if re.search(p, t2):
            return True

    return False


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
    bar_len = 30
    filled = int(done / total * bar_len)
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

                if not has_3_plus_exp(text):
                    continue

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
        msg["Subject"] = "Application for QA Automation / SDET Role"
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

        # Long cooldown after N emails
        if sent % COOLDOWN_EVERY == 0 and sent < total:
            cd = random.uniform(COOLDOWN_MIN_SECONDS, COOLDOWN_MAX_SECONDS)
            print(f"\n🛑 Long cooldown after {sent} emails: {cd:.1f}s")
            time.sleep(cd)

    if USE_RICH:
        progress.stop()

    server.quit()

    update_log(LOG_FILE, sent)

    print(f"\n🎉 DONE — Sent {sent} emails successfully.")


if __name__ == "__main__":
    main()
