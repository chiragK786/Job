#!/usr/bin/env python3
"""
MANUAL EMAIL SENDER
- Email addresses manually entered (CSV file or direct list)
- Port 587 (STARTTLS) primary, 465 (SSL) fallback
- Auto-retry, batching, rate limiting all included
"""

import re
import csv
import os
import time
import random
import mimetypes
import smtplib
import logging
from email.message import EmailMessage
from datetime import date
from pathlib import Path
from typing import Set, List, Dict, Union

# ─────────────────────────────────────────────
#  ✅ ADD YOUR EMAILS HERE (manual list)
# ─────────────────────────────────────────────
MANUAL_EMAILS: List[str] = ["ayushi.sharma1@orcapod.work"
                            #hr@company1.com",


                            # "recruiter@company2.com",
                            # "jobs@company3.com",
                            # Add as many as you need
                            ]

# ─────────────────────────────────────────────
#  ✅ OR LOAD FROM CSV FILE
#  CSV should have only one column: Email
#  Example: manual_emails.csv
#    Email
#    hr@company1.com
#    recruiter@company2.com
# ─────────────────────────────────────────────
MANUAL_EMAILS_CSV: str = ""  # Example: "/Users/yourname/Desktop/manual_emails.csv"
# Leave blank if using the list above

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
ATTACHMENT_PATH = (
    "/Users/chiragkhanduja/PycharmProjects/PythonProject11/"
    "Chirag_Khanduja_QA_Resume_AI_SDET.pdf"
)

EMAIL_ADDRESS = "chiragkhanduja786@gmail.com"
EMAIL_PASSWORD = "ivci swwm gwfx btku"

BASE_DIR = Path("/Users/chiragkhanduja/PycharmProjects/PythonProject11")
LOG_FILE = BASE_DIR / "email_log.csv"
APP_LOG_FILE = BASE_DIR / "app.log"

EXCLUDED_DOMAINS: Set[str] = {"squareboat.com", "hudle.in", "programming.com"}
EXCLUDED_EMAILS: Set[str] = {"info@jobcurator.in"}

DRY_RUN = False  # Set to True for testing only (no emails will be sent)

# ─────────────────────────────────────────────
#  SMTP SETTINGS
# ─────────────────────────────────────────────
SMTP_TIMEOUT = 30
SMTP_MAX_RETRIES = 3
SMTP_RETRY_WAIT = (10, 20)

# ─────────────────────────────────────────────
#  RATE LIMITING
# ─────────────────────────────────────────────
PER_EMAIL_DELAY = (3, 7)
DOMAIN_BURST_SIZE = 2
DOMAIN_BURST_PAUSE = (15, 30)
BATCH_SIZE = 40
SESSION_BREAK = (600, 1200)
MAX_PER_HOUR = 55
DAILY_CAP = 250

# ─────────────────────────────────────────────
#  EMAIL CONTENT
# ─────────────────────────────────────────────
EMAIL_SUBJECT = (
    "QA Automation Engineer / SDET "
    "— 4 Years of Experience in Test Automation & CI/CD Integration"
)

EMAIL_BODY = """\
<p>Dear Hiring Manager,</p>

<p>
I am writing to express my strong interest in a QA Automation Engineer / SDET opportunity
at your organization. With <strong>4 years</strong> of hands-on experience building and scaling
test automation frameworks, I am confident in my ability to deliver measurable improvements
in software quality, release velocity, and test coverage.
</p>

<p><strong>Here is a brief overview of what I bring to the role:</strong></p>
<ul>
  <li>
    <strong>Automation Frameworks:</strong> Hands-on expertise with Playwright, Selenium, and
    Appium to design and maintain robust end-to-end and cross-platform test suites.
  </li>
  <li>
    <strong>API &amp; Integration Testing:</strong> Extensive experience validating REST APIs
    using Postman and building automated integration checks for reliable service communication.
  </li>
  <li>
    <strong>Test Strategy &amp; Engineering:</strong> Designed regression suites and
    release-ready test plans that reduced manual testing effort and improved defect detection.
  </li>
  <li>
    <strong>CI/CD Integration:</strong> Integrated automated test pipelines into CI/CD
    workflows using Pytest, enabling fast and reliable release cycles.
  </li>
  <li>
    <strong>Cross-Functional Collaboration:</strong> Proven ability to work alongside
    developers, product managers, and business stakeholders to align QA with product goals.
  </li>
</ul>

<p>
I am particularly drawn to organizations that value engineering quality and shift-left
testing practices. I thrive in environments where test automation is treated as a
first-class engineering discipline.
</p>

<p>
I have attached my resume for your consideration. I would welcome the opportunity to connect
for a brief 15-minute call to discuss how my experience aligns with your team's needs.
</p>

<p>Thank you for your time and consideration. I look forward to hearing from you.</p>

<p>
Warm regards,<br>
<strong>Chirag Khanduja</strong><br>
QA Automation Engineer | SDET<br>
903-422-6868
</p>
"""


# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
def setup_logging() -> logging.Logger:
    APP_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("email_sender")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(APP_LOG_FILE)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


log = setup_logging()

# ─────────────────────────────────────────────
#  EMAIL LOADING — manual list or CSV
# ─────────────────────────────────────────────
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,7}")


def load_manual_emails() -> List[str]:
    """Load emails from MANUAL_EMAILS list + optional CSV file."""
    emails: List[str] = []

    # 1. From direct list
    for e in MANUAL_EMAILS:
        e = e.strip().lower()
        if EMAIL_RE.fullmatch(e):
            emails.append(e)
        else:
            log.warning("Invalid email skipped: %s", e)

    # 2. From CSV file (if path provided)
    if MANUAL_EMAILS_CSV:
        csv_path = Path(MANUAL_EMAILS_CSV)
        if not csv_path.exists():
            log.error("CSV file not found: %s", MANUAL_EMAILS_CSV)
        else:
            with csv_path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                # Column name is flexible: Email, email, EMAIL, all accepted
                col = next(
                    (c for c in (reader.fieldnames or []) if c.strip().lower() == "email"),
                    None
                )
                if col is None:
                    # No header — treat first column as email
                    f.seek(0)
                    plain_reader = csv.reader(f)
                    for row in plain_reader:
                        if row:
                            e = row[0].strip().lower()
                            if EMAIL_RE.fullmatch(e):
                                emails.append(e)
                else:
                    for row in reader:
                        e = row[col].strip().lower()
                        if EMAIL_RE.fullmatch(e):
                            emails.append(e)
                        else:
                            log.warning("Invalid email in CSV skipped: %s", row[col])
            log.info("Loaded from CSV: %s", csv_path.name)

    # Filter excluded
    filtered = []
    for e in emails:
        domain = e.split("@")[-1]
        if domain in EXCLUDED_DOMAINS:
            log.debug("Excluded domain skipped: %s", e)
        elif e in EXCLUDED_EMAILS:
            log.debug("Excluded email skipped: %s", e)
        else:
            filtered.append(e)

    # Deduplicate (preserve order)
    seen = set()
    unique = []
    for e in filtered:
        if e not in seen:
            seen.add(e)
            unique.append(e)

    log.info("Total unique valid emails loaded: %d", len(unique))
    return unique


# ─────────────────────────────────────────────
#  DAILY LOG
# ─────────────────────────────────────────────
def get_today_sent_count() -> int:
    today = date.today().isoformat()
    if not LOG_FILE.exists():
        return 0
    with LOG_FILE.open(newline="") as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if row and row[0] == today:
            return int(row[1])
    return 0


def update_daily_log(count: int) -> None:
    today = date.today().isoformat()
    rows: List[List[str]] = [["Date", "Count"]]
    if LOG_FILE.exists():
        with LOG_FILE.open(newline="") as f:
            rows = list(csv.reader(f))
    updated = False
    for row in rows[1:]:
        if row and row[0] == today:
            row[1] = str(int(row[1]) + count)
            updated = True
            break
    if not updated:
        rows.append([today, str(count)])
    with LOG_FILE.open("w", newline="") as f:
        csv.writer(f).writerows(rows)


# ─────────────────────────────────────────────
#  HOURLY RATE LIMITER
# ─────────────────────────────────────────────
class HourlyRateLimiter:
    def __init__(self, max_per_hour: int):
        self.max_per_hour = max_per_hour
        self.timestamps: List[float] = []

    def wait_if_needed(self) -> None:
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t < 3600]
        if len(self.timestamps) >= self.max_per_hour:
            oldest = self.timestamps[0]
            wait_secs = 3600 - (now - oldest) + 5
            log.info("⏳ Hourly limit reached. Waiting %.0f minutes…", wait_secs / 60)
            time.sleep(wait_secs)
            self.timestamps = []

    def record(self) -> None:
        self.timestamps.append(time.time())


# ─────────────────────────────────────────────
#  SMTP
# ─────────────────────────────────────────────
def build_message(to_email: str, attachment_data: bytes,
                  attach_mime: str, attach_name: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = EMAIL_SUBJECT
    msg.add_alternative(EMAIL_BODY, subtype="html")
    maintype, subtype = attach_mime.split("/", 1)
    msg.add_attachment(attachment_data, maintype=maintype,
                       subtype=subtype, filename=attach_name)
    return msg


def _try_starttls(timeout: int) -> smtplib.SMTP:
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=timeout)
    server.ehlo();
    server.starttls();
    server.ehlo()
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    return server


def _try_ssl(timeout: int) -> smtplib.SMTP_SSL:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=timeout)
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    return server


def connect_smtp() -> Union[smtplib.SMTP, smtplib.SMTP_SSL]:
    for attempt in range(1, SMTP_MAX_RETRIES + 1):
        try:
            server = _try_starttls(SMTP_TIMEOUT)
            log.info("✅ Connected via 587 (STARTTLS) — attempt %d", attempt)
            return server
        except Exception as exc:
            log.warning("⚠️  Port 587 failed (%d/%d): %s", attempt, SMTP_MAX_RETRIES, exc)
        try:
            server = _try_ssl(SMTP_TIMEOUT)
            log.info("✅ Connected via 465 (SSL) — attempt %d", attempt)
            return server
        except Exception as exc:
            log.warning("⚠️  Port 465 failed (%d/%d): %s", attempt, SMTP_MAX_RETRIES, exc)
        if attempt < SMTP_MAX_RETRIES:
            wait = random.uniform(*SMTP_RETRY_WAIT)
            log.info("🔄 Retrying in %.0f seconds…", wait)
            time.sleep(wait)
    raise RuntimeError("❌ Cannot connect to Gmail SMTP. Check internet connection and firewall settings.")


# ─────────────────────────────────────────────
#  PROGRESS
# ─────────────────────────────────────────────
def simple_bar(done: int, total: int) -> None:
    if total == 0:
        return
    filled = int(done / total * 45)
    bar = "█" * filled + "─" * (45 - filled)
    print(f"\r[{bar}] {done}/{total}", end="", flush=True)


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main() -> None:
    attach_path = Path(ATTACHMENT_PATH)
    if not attach_path.exists():
        raise FileNotFoundError(f"Resume file not found: {attach_path}")

    already_today = get_today_sent_count()
    remaining_cap = DAILY_CAP - already_today
    if remaining_cap <= 0:
        log.info("📅 Daily cap (%d) already reached today. Run again tomorrow.", DAILY_CAP)
        return
    log.info("📅 Daily cap: %d | Already sent today: %d | Remaining: %d",
             DAILY_CAP, already_today, remaining_cap)

    # ── Load emails ────────────────────────────────────────────────────
    all_emails = load_manual_emails()
    send_list = all_emails[:remaining_cap]

    log.info("Total emails to send: %d", len(send_list))

    if not send_list:
        log.info("No emails to send — script exiting.")
        return

    if DRY_RUN:
        log.info("🧪 DRY RUN MODE — no emails will be sent. Recipients:")
        for e in send_list:
            log.info("  → %s", e)
        log.info("Set DRY_RUN=False to send actual emails.")
        return

    attach_data = attach_path.read_bytes()
    attach_mime = mimetypes.guess_type(str(attach_path))[0] or "application/octet-stream"
    attach_name = attach_path.name

    total = len(send_list)
    sent_count = 0
    domain_count: Dict[str, int] = {}
    rate_limiter = HourlyRateLimiter(MAX_PER_HOUR)

    log.info("🚀 Starting to send: %d emails | Batch size: %d | Max per hour: %d",
             total, BATCH_SIZE, MAX_PER_HOUR)

    server = connect_smtp()

    for i, to_email in enumerate(send_list):

        # ── Batch break ────────────────────────────────────────────────
        if i > 0 and i % BATCH_SIZE == 0:
            pause = random.uniform(*SESSION_BREAK)
            log.info("☕ Batch complete (%d sent). Taking break for %.0f minutes…",
                     sent_count, pause / 60)
            try:
                server.quit()
            except Exception:
                pass
            elapsed = 0
            while elapsed < pause:
                chunk = min(300, pause - elapsed)
                time.sleep(chunk)
                elapsed += chunk
                if pause - elapsed > 0:
                    log.info("⏰ Resuming in %.0f minutes…", (pause - elapsed) / 60)
            server = connect_smtp()

        rate_limiter.wait_if_needed()

        msg = build_message(to_email, attach_data, attach_mime, attach_name)
        try:
            server.send_message(msg)
            sent_count += 1
            rate_limiter.record()
            log.info("✔ [%d/%d] Sent to → %s", sent_count, total, to_email)

        except smtplib.SMTPRecipientsRefused:
            log.warning("✘ Refused: %s", to_email)

        except smtplib.SMTPServerDisconnected:
            log.warning("🔌 Server disconnected — reconnecting…")
            try:
                server = connect_smtp()
                server.send_message(msg)
                sent_count += 1
                rate_limiter.record()
                log.info("✔ [%d/%d] Sent (retry) → %s", sent_count, total, to_email)
            except Exception as exc:
                log.error("✘ Retry failed %s: %s", to_email, exc)

        except smtplib.SMTPException as exc:
            log.error("✘ SMTP error %s: %s", to_email, exc)

        except Exception as exc:
            log.error("✘ Unexpected error %s: %s", to_email, exc)

        simple_bar(sent_count, total)

        domain = to_email.split("@")[-1]
        domain_count[domain] = domain_count.get(domain, 0) + 1
        if domain_count[domain] % DOMAIN_BURST_SIZE == 0:
            pause = random.uniform(*DOMAIN_BURST_PAUSE)
            time.sleep(pause)

        time.sleep(random.uniform(*PER_EMAIL_DELAY))

    print()  # newline after progress bar

    try:
        server.quit()
    except Exception:
        pass

    update_daily_log(sent_count)
    log.info("🎉 Complete — sent %d/%d emails.", sent_count, total)


if __name__ == "__main__":
    main()
