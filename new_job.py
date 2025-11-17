#!/usr/bin/env python3
"""
Final Personalized Email Sender
- Extracts emails from PDF pages that mention >=3 years experience.
- Advanced PDF company detection (but email uses 'your esteemed organization' phrase).
- Auto-uses referral template if page contains referral keywords.
- Three body variants + referral variant.
- Tracks sent emails, logs daily counts, throttles safely, deletes PDF after sending.
"""

import re
import csv
import os
import pdfplumber
import mimetypes
import smtplib
import time
import random
from email.message import EmailMessage
from datetime import date, datetime
from typing import Dict, Set, Optional

# ---------------- CONFIG - EDIT THESE ----------------
pdf_path = "/Users/chiragkhanduja/Downloads/TestingJobs_FullList (6).pdf"
attachment_path = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Chirag_Khanduja_Sr_QA_SDET_AI_Resume_Latest.pdf"
EMAIL_ADDRESS = "chiragkhanduja786@gmail.com"
EMAIL_PASSWORD = "xshh zjbn ckjg yryl"  # Gmail App Password (app password recommended)
sent_emails_file = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/sent_emails.csv"
log_file = "/Users/chiragkhanduja/PycharmProjects/PythonProject11/email_log.csv"
excluded_domains = ['@squareboat.com', '@hudle.in', '@infosys.com', '@cgi.com', '@rayosys.com', '@cognizant.com']

# Phrase to use in emails instead of detected company name
ORG_PHRASE = "your esteemed organization"

# ---------------- EXPERIENCE FILTER PATTERNS (>=3 years) ----------------
EXP_PATTERNS = [
    r"3\+\s*years",
    r"\bat\s+least\s+3\s+years\b",
    r"\bminimum\s+3\s+years\b",
    r"\b3\s*to\s*5\s*years\b",
    r"\b3\s*-\s*5\s*years\b",
    r"\b3\s*or\s+more\s+years\b",
    r"\b3\s+years\b",
]

# Referral detection words (if the page mentions these we use referral body)
REFERRAL_KEYWORDS = [r"\brefer\b", r"\breferral\b", r"\breferred\b", r"\bcan you refer\b", r"\bplease refer\b"]

# PDF company detection patterns (optional, not used in body text but available)
PDF_COMPANY_PATTERNS = [
    r"\b([A-Z][A-Za-z0-9& ]{2,60}?)\s+(?:Private|Pvt|Solutions|Technologies|Labs|Inc|LLC|Ltd)\b",
    r"Company[:\-\s]+([A-Z][A-Za-z0-9 &]{2,60})",
    r"Hiring for[:\-\s]+([A-Z][A-Za-z0-9 &]{2,60})",
]

# ---------------- HELPERS ----------------
def extract_name(email: str) -> str:
    local = re.sub(r'[^a-zA-Z._\-\s]', ' ', email.split('@')[0])
    parts = [p for p in re.split(r'[._\-\s]+', local) if p]
    return " ".join(p.capitalize() for p in parts) if parts else "Hiring Manager"

def extract_company_from_domain(email: str) -> str:
    domain = email.split('@')[1].lower()
    personal_domains = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com", "protonmail.com"}
    if domain in personal_domains:
        return "Hiring Team"
    return domain.split('.')[0].replace('-', ' ').title()

def detect_company_from_pdf(text: str) -> Optional[str]:
    for pattern in PDF_COMPANY_PATTERNS:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip().title()
    return None

def detect_role_from_text(text: str) -> str:
    t = (text or "").lower()
    mapping = {
        "sdet": ["sdet", "software development engineer"],
        "automation": ["automation", "selenium", "robot framework", "cypress", "playwright"],
        "api": ["api", "postman", "rest", "backend"],
        "performance": ["performance", "load", "locust", "jmeter", "stress"],
    }
    for role, keys in mapping.items():
        if any(k in t for k in keys):
            return role
    return "automation"

def subject_line(role: str) -> str:
    return {
        "sdet": "Application for SDET Role — Automation & QA Engineering",
        "automation": "Application for QA Automation Engineer Position",
        "api": "Application for API QA Engineer Position",
        "performance": "Application for Performance / Load Test Engineer Position",
    }.get(role, "Application for QA Engineer Position")

def page_mentions_experience(text: str) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in EXP_PATTERNS)

def page_mentions_referral(text: str) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in REFERRAL_KEYWORDS)

# ---------------- EMAIL BODY TEMPLATES ----------------
def body_super_formal(name: str) -> str:
    return f"""\
<p>Dear <b>{name}</b>,</p>
<p>I hope this message finds you well. I am writing to formally express my interest in the role at <b>{ORG_PHRASE}</b>. As an ISTQB-certified Senior QA Engineer with over three years of experience in automation, API validation, and performance testing, I bring a combination of technical depth and process ownership.</p>
<p>I have hands-on experience in <b>Selenium (Java/Python)</b>, <b>Robot Framework</b>, <b>Cypress</b>, <b>Playwright</b>, <b>Postman</b>, <b>JMeter</b>, and <b>Locust</b>, and have integrated automation into CI/CD (Jenkins). I have contributed to large-scale platforms and helped teams reduce regression time and improve release reliability.</p>
<p>I would appreciate the opportunity to discuss how my background aligns with your requirements.</p>
<p>Sincerely,<br><b>Chirag Khanduja<br>9034226868</b></p>"""

def body_recruiter_friendly(name: str) -> str:
    return f"""\
<p>Dear <b>{name}</b>,</p>
<p>Quick summary of my fit for the role at <b>{ORG_PHRASE}</b>:</p>
<ul>
  <li><b>3+ years</b> in QA Automation, API Testing & Performance Testing</li>
  <li>Automation: <b>Selenium, Robot Framework, Cypress, Playwright</b></li>
  <li>API: <b>Postman</b> (collections & automation)</li>
  <li>Performance: <b>JMeter, Locust</b></li>
  <li>Worked across multiple products: ATS, Harbor, Woobly Genie, Hudle, GrayPorter, and more</li>
  <li>CI/CD: <b>Jenkins</b></li>
  <li>Awards: <b>Top Performer (2024)</b>, <b>Excellence Award (2025)</b></li>
</ul>
<p>I have attached my resume and would welcome a brief conversation.</p>
<p>Regards,<br><b>Chirag Khanduja<br>9034226868</b></p>"""

def body_anti_spam(name: str) -> str:
    openers = [
        "Hope you're doing well. I recently learned about an opportunity at your organization.",
        "Warm greetings. I noticed an opening that aligns with my skill set.",
        "Hope your day is going well. I wanted to express interest in the role.",
        "Trust you are doing great. I came across this requirement recently."
    ]
    opener = random.choice(openers)
    return f"""\
<p>Dear <b>{name}</b>,</p>
<p>{opener}</p>
<p>I have 3+ years of hands-on experience in Automation (Selenium, Robot Framework, Cypress, Playwright), API Testing (Postman), and Performance Testing (JMeter, Locust). I have contributed to multiple products across SaaS, EdTech and Healthcare domains.</p>
<p>I would be glad to discuss how I can support QA efforts at <b>{ORG_PHRASE}</b>.</p>
<p>Regards,<br><b>Chirag Khanduja<br>9034226868</b></p>"""

def body_referral(name: str) -> str:
    return f"""\
<p>Dear <b>{name}</b>,</p>
<p>Thank you for offering to refer my profile. I truly appreciate your support.</p>
<p>I am excited to express my interest in the role at <b>{ORG_PHRASE}</b>. With over three years of hands-on experience in Automation (Selenium, Robot Framework, Cypress, Playwright), API testing (Postman), and performance testing (JMeter, Locust), I believe I can contribute effectively.</p>
<p>Please feel free to share my resume internally. I would be grateful for any assistance in getting my application considered.</p>
<p>Regards,<br><b>Chirag Khanduja<br>9034226868</b></p>"""

def choose_body_for_page(name: str, page_has_referral: bool) -> str:
    if page_has_referral:
        return body_referral(name)
    # randomize among three main templates
    return random.choice([body_super_formal, body_recruiter_friendly, body_anti_spam])(name)

# ---------------- MAIN FLOW ----------------
def main():
    # sanity checks
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not os.path.exists(attachment_path):
        raise FileNotFoundError(f"Attachment not found: {attachment_path}")

    # Extract emails along with page-level context (experience-check + referral-check)
    page_email_map: Dict[str, Dict] = {}  # email -> { 'page_text': str, 'page_has_referral': bool }
    all_text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            all_text += "\n" + page_text

            # Only consider emails on pages that mention >=3 years experience
            if not page_mentions_experience(page_text):
                continue

            page_has_ref = page_mentions_referral(page_text)

            # find emails on this page
            found = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}", page_text)
            for e in found:
                e_low = e.lower().strip()
                if e_low == "info@jobcurator.in":
                    continue
                if any(e_low.endswith(d) for d in excluded_domains):
                    continue
                # record email with page flags
                page_email_map[e_low] = {
                    "page_text": page_text,
                    "page_has_referral": page_has_ref
                }

    if not page_email_map:
        print("⚠ No emails found on pages that mention >=3 years experience. Exiting.")
        return

    role = detect_role_from_text(all_text)
    print(f"✔ Detected role-style: {role}; found {len(page_email_map)} emails matching experience >=3yrs")

    # try to detect a company from PDF for info (we won't insert company into email body)
    pdf_company = detect_company_from_pdf(all_text)
    if pdf_company:
        print(f"ℹ PDF-level detected company: {pdf_company} (we will still use '{ORG_PHRASE}' in emails)")

    # load sent list
    sent_before: Set[str] = set()
    if os.path.exists(sent_emails_file):
        with open(sent_emails_file, newline='') as sf:
            reader = csv.reader(sf)
            sent_before = {row[0].strip().lower() for row in reader if row}

    # prepare list to send
    emails_to_send = [e for e in sorted(page_email_map.keys()) if e not in sent_before]
    if not emails_to_send:
        print("No new emails to send (all were already sent). Exiting.")
        return

    # Setup SMTP
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

    mime_type, _ = mimetypes.guess_type(attachment_path)
    mime_type = mime_type or "application/octet-stream"
    maintype, subtype = mime_type.split("/")

    sent_count = 0
    today_str = date.today().strftime("%Y-%m-%d")

    # send loop
    for idx, to_email in enumerate(emails_to_send, start=1):
        name = extract_name(to_email)

        # Page-level referral flag
        page_has_ref = page_email_map[to_email]["page_has_referral"]

        # Choose body (if page has referral -> referral template)
        body_html = choose_body_for_page(name, page_has_ref)

        # subject depends on role
        subj = subject_line(role)

        # build message
        msg = EmailMessage()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subj
        msg.add_alternative(body_html, subtype="html")

        # attach resume
        with open(attachment_path, "rb") as af:
            msg.add_attachment(af.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(attachment_path))

        # send
        try:
            server.send_message(msg)
            sent_count += 1
            print(f"✔ Sent ({sent_count}): {to_email}")

            # persist in sent_emails_file
            os.makedirs(os.path.dirname(sent_emails_file), exist_ok=True)
            with open(sent_emails_file, "a", newline='') as sf:
                csv.writer(sf).writerow([to_email])

            # throttle with slight randomization
            time.sleep(1.5 + random.random() * 0.6)
            if sent_count % 50 == 0:
                print("⏳ Cooling down 5 seconds...")
                time.sleep(5)

        except Exception as exc:
            print(f"❌ Failed to send to {to_email}: {exc}")

    # close SMTP
    try:
        server.quit()
    except Exception:
        pass

    print(f"\n📨 DONE — Sent {sent_count} emails")

    # update daily log
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    rows = []
    if os.path.exists(log_file):
        with open(log_file, newline='') as lf:
            rows = list(csv.reader(lf))
    else:
        rows = [["Date", "EmailsSent"]]

    found = False
    for r in rows[1:]:
        if r and r[0] == today_str:
            r[1] = str(int(r[1]) + sent_count)
            found = True
            break
    if not found:
        rows.append([today_str, str(sent_count)])

    with open(log_file, "w", newline='') as lf:
        csv.writer(lf).writerows(rows)

    # delete source PDF automatically
    try:
        os.remove(pdf_path)
        print(f"🗑️ Deleted PDF file: {pdf_path}")
    except Exception as e:
        print(f"⚠️ Could not delete PDF file: {e}")

if __name__ == "__main__":
    main()
