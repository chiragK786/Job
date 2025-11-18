#!/usr/bin/env python3
"""
Personalized Email Sender (Experience filter removed) with anti-spam and progress bar.

Updates in this version:
✔ Daily limit removed completely.
✔ Cooldown after every 20 emails (2–5 minutes).
✔ Everything else same.
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
from typing import Dict, Set, Optional

# ---------------- CONFIG ----------------
PDF_PATH = "/Users/chiragkhanduja/Downloads/TestingJobs_FullList (6).pdf"
ATTACHMENT_PATH = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Chirag_Khanduja_Sr_QA_SDET_AI_Resume_Latest.pdf"

EMAIL_ADDRESS = "chiragkhanduja786@gmail.com"
EMAIL_PASSWORD = "xshh zjbn ckjg yryl"

SENT_EMAILS_FILE = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/sent_emails.csv"
LOG_FILE = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/email_log.csv"

EXCLUDED_DOMAINS = [
    '@squareboat.com', '@hudle.in', '@infosys.com',
    '@cgi.com', '@rayosys.com', '@cognizant.com'
]

ORG_PHRASE = "your esteemed organization"

REFERRAL_KEYWORDS = [
    r"\brefer\b", r"\breferral\b", r"\breferred\b",
    r"\bcan you refer\b", r"\bplease refer\b"
]

PDF_COMPANY_PATTERNS = [
    r"\b([A-Z][A-Za-z0-9& ]{2,60}?)\s+(?:Private|Pvt|Solutions|Technologies|Labs|Inc|LLC|Ltd)\b",
    r"Company[:\-\s]+([A-Z][A-Za-z0-9 &]{2,60})",
    r"Hiring for[:\-\s]+([A-Z][A-Za-z0-9 &]{2,60})",
]

# Anti-spam:
PER_EMAIL_DELAY_MIN = 1.8
PER_EMAIL_DELAY_MAX = 4.2
COOLDOWN_EVERY = 30                     # CHANGED
COOLDOWN_MIN_SECONDS = 120              # 2 minutes
COOLDOWN_MAX_SECONDS = 300              # 5 minutes

DOMAIN_BURST_THRESHOLD = 3
DOMAIN_BURST_PAUSE = (10, 25)

# ---------------- HELPERS ----------------
def extract_name(email: str) -> str:
    local = re.sub(r'[^a-zA-Z._\-\s]', ' ', email.split('@')[0])
    parts = [p for p in re.split(r'[._\-\s]+', local) if p]
    return " ".join(p.capitalize() for p in parts) if parts else "Hiring Manager"

def detect_company_from_pdf(text: str) -> Optional[str]:
    for p in PDF_COMPANY_PATTERNS:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip().title()
    return None

def detect_role_from_text(text: str) -> str:
    t = text.lower()
    mapping = {
        "sdet": ["sdet", "software development engineer"],
        "automation": ["automation", "selenium", "robot framework", "cypress", "playwright"],
        "api": ["api", "postman", "rest"],
        "performance": ["performance", "load", "locust", "jmeter"],
    }
    for role, keys in mapping.items():
        if any(k in t for k in keys):
            return role
    return "automation"

def page_mentions_referral(t: str) -> bool:
    return any(re.search(k, t, flags=re.IGNORECASE) for k in REFERRAL_KEYWORDS)

def subject_line(role: str) -> str:
    return {
        "sdet": "Application for SDET Role — Automation & QA Engineering",
        "automation": "Application for QA Automation Engineer Position",
        "api": "Application for API QA Engineer Position",
        "performance": "Application for Performance / Load Test Engineer Position",
    }.get(role, "Application for QA Engineer Position")

# ---------------- TEMPLATES ----------------
def body_super_formal(name): return f"""<p>Dear <b>{name}</b>,</p>
<p>I hope this message finds you well...</p>"""

def body_recruiter_friendly(name): return f"""<p>Dear <b>{name}</b>,</p>
<p>Quick summary...</p>"""

def body_anti_spam(name):
    opener = random.choice([
        "Hope you're doing well.",
        "Warm greetings.",
        "Hope your day is going well.",
        "Trust you're doing great."
    ])
    return f"""<p>Dear <b>{name}</b>,</p><p>{opener}</p>"""

def body_referral(name): return f"""<p>Dear <b>{name}</b>,</p>
<p>Thank you for offering to refer me...</p>"""

def choose_body(name, is_ref):
    return body_referral(name) if is_ref else random.choice(
        [body_super_formal, body_recruiter_friendly, body_anti_spam])(name)

# ---------------- STORAGE ----------------
def load_sent_emails(f):
    if not os.path.exists(f): return set()
    return {row[0].strip().lower() for row in csv.reader(open(f)) if row}

def append_sent(f, email):
    os.makedirs(os.path.dirname(f), exist_ok=True)
    csv.writer(open(f, "a")).writerow([email])

# ---------------- PROGRESS BAR ----------------
USE_RICH = True
try:
    from rich.progress import Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, TextColumn
except:
    USE_RICH = False

def rich_progress(total):
    return Progress(
        TextColumn("[bold green]Sending emails:"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        TimeRemainingColumn()
    )

def simple_progress(done, total):
    bar_len = 30
    filled = int((done/total)*bar_len)
    bar = "█"*filled + "-"*(bar_len-filled)
    print(f"\r[{bar}] {done}/{total}", end="")

# ---------------- MAIN ----------------
def main():
    if not os.path.exists(PDF_PATH): raise FileNotFoundError(PDF_PATH)
    if not os.path.exists(ATTACHMENT_PATH): raise FileNotFoundError(ATTACHMENT_PATH)

    emails = {}
    all_txt = ""

    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_txt += "\n" + text
            has_ref = page_mentions_referral(text)

            found = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}", text)
            for e in found:
                e = e.lower().strip()
                if any(e.endswith(d) for d in EXCLUDED_DOMAINS): continue
                if e == "info@jobcurator.in": continue
                emails[e] = {"ref": has_ref}

    role = detect_role_from_text(all_txt)
    send_list = sorted(emails.keys())

    # remove already sent
    sent_before = load_sent_emails(SENT_EMAILS_FILE)
    send_list = [e for e in send_list if e not in sent_before]
    if not send_list:
        print("✔ No new emails.")
        return

    # SMTP
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

    mime = mimetypes.guess_type(ATTACHMENT_PATH)[0] or "application/octet-stream"
    maintype, subtype = mime.split("/")

    total = len(send_list)
    sent = 0
    domain_count = {}

    # Progress UI
    if USE_RICH:
        progress = rich_progress(total)
        progress.start()
        t = progress.add_task("send", total=total)
    else:
        print("Rich not available — simple progress.")

    for to_email in send_list:
        name = extract_name(to_email)
        ref_flag = emails[to_email]["ref"]

        msg = EmailMessage()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject_line(role)
        msg.add_alternative(choose_body(name, ref_flag), subtype="html")

        with open(ATTACHMENT_PATH, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype,
                               filename=os.path.basename(ATTACHMENT_PATH))

        try:
            server.send_message(msg)
            sent += 1
            append_sent(SENT_EMAILS_FILE, to_email)
            print(f"\n✔ Sent {sent}/{total}: {to_email}")
        except Exception as e:
            print(f"\n❌ Failed: {to_email} — {e}")

        # progress update
        if USE_RICH:
            progress.update(t, advance=1)
        else:
            simple_progress(sent, total)

        # domain burst control
        domain = to_email.split("@")[1]
        domain_count[domain] = domain_count.get(domain, 0)+1
        if domain_count[domain] % DOMAIN_BURST_THRESHOLD == 0:
            pause = random.uniform(*DOMAIN_BURST_PAUSE)
            print(f"\n⏸️ Domain burst pause {domain}: {int(pause)}s")
            time.sleep(pause)

        # per-email delay
        time.sleep(random.uniform(PER_EMAIL_DELAY_MIN, PER_EMAIL_DELAY_MAX))

        # long cooldown every 20 emails (changed)
        if sent % COOLDOWN_EVERY == 0 and sent < total:
            cooldown = random.uniform(COOLDOWN_MIN_SECONDS, COOLDOWN_MAX_SECONDS)
            print(f"\n🛑 Cooldown after {sent} emails: {int(cooldown)}s")
            time.sleep(cooldown)

    if USE_RICH:
        progress.stop()

    server.quit()

    # log count
    today = date.today().strftime("%Y-%m-%d")
    rows = [["Date", "Count"]]
    if os.path.exists(LOG_FILE):
        rows = list(csv.reader(open(LOG_FILE)))
    found = False
    for r in rows[1:]:
        if r[0] == today:
            r[1] = str(int(r[1]) + sent)
            found = True
    if not found:
        rows.append([today, str(sent)])
    csv.writer(open(LOG_FILE, "w")).writerows(rows)

    # delete PDF
    try:
        os.remove(PDF_PATH)
        print(f"\n🗑️ Deleted: {PDF_PATH}")
    except:
        pass

    print(f"\n📨 DONE — Sent {sent} emails.")

if __name__ == "__main__":
    main()
