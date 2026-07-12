#!/usr/bin/env python3
"""
COLD EMAIL SENDER (Personalized)
----------------------------------------------------------------
- Recipients loaded from a CSV file (with merge fields: name, company, etc.)
- Credentials loaded from a .env file (NEVER hardcoded in this script)
- Port 587 (STARTTLS) primary, 465 (SSL) fallback
- Auto-retry, batching, hourly + daily rate limiting
- Unsubscribe / opt-out line included automatically
- Sent-log (CSV) so you never accidentally email the same person twice
----------------------------------------------------------------

SETUP STEPS:
1. pip install python-dotenv
2. Create a file named ".env" in the same folder as this script:

       EMAIL_ADDRESS=youraddress@gmail.com
       EMAIL_PASSWORD=your_16_char_app_password

   (Generate an App Password at: Google Account -> Security -> App Passwords.
    Do NOT use your normal Gmail password — it will not work with 2FA enabled,
    and you should never put real passwords in scripts you share or paste anywhere.)

3. Create "recipients.csv" in the same folder with these columns:

       email,first_name,company,role
       hr@company1.com,Asha,Company1,Hiring Manager
       recruiter@company2.com,,Company2,
       jobs@company3.com,Raj,Company3,Recruiter

   Only "email" is required. Blank fields fall back to generic wording.

4. Edit the CONFIG section below (subject, body template, attachment path).

5. Test first with DRY_RUN = True (no emails actually sent — just previewed/logged).

6. Set DRY_RUN = False when you're ready to actually send.
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
from typing import Set, List, Dict, Union, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    raise SystemExit(
        "Missing dependency. Run: pip install python-dotenv  "
        "(use --break-system-packages if on a system Python install)"
    )

# ─────────────────────────────────────────────
#  PATHS / CONFIG — edit these
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

ENV_FILE = BASE_DIR / ".env"
RECIPIENTS_CSV = BASE_DIR / "recipients.csv"
ATTACHMENT_PATH = BASE_DIR / "resume.pdf"          # <-- change to your actual file

LOG_FILE = BASE_DIR / "email_log.csv"              # daily send-count log
SENT_LOG_FILE = BASE_DIR / "sent_recipients.csv"   # who has already been emailed
APP_LOG_FILE = BASE_DIR / "app.log"

EXCLUDED_DOMAINS: Set[str] = {"squareboat.com", "hudle.in", "programming.com"}
EXCLUDED_EMAILS: Set[str] = {"info@jobcurator.in"}

DRY_RUN = True  # <-- keep True until you've checked a preview, then set False

# ─────────────────────────────────────────────
#  SMTP SETTINGS
# ─────────────────────────────────────────────
SMTP_TIMEOUT = 30
SMTP_MAX_RETRIES = 3
SMTP_RETRY_WAIT = (10, 20)

# ─────────────────────────────────────────────
#  RATE LIMITING (keep these conservative — Gmail will flag/suspend
#  accounts that send too fast or too many cold emails)
# ─────────────────────────────────────────────
PER_EMAIL_DELAY = (3, 7)
DOMAIN_BURST_SIZE = 2
DOMAIN_BURST_PAUSE = (15, 30)
BATCH_SIZE = 40
SESSION_BREAK = (600, 1200)
MAX_PER_HOUR = 55
DAILY_CAP = 250

# ─────────────────────────────────────────────
#  EMAIL CONTENT — merge fields: {first_name} {company} {role}
#  These are filled in per-recipient from the CSV. Missing values
#  fall back to sensible generic text (see personalize() below).
# ─────────────────────────────────────────────
EMAIL_SUBJECT_TEMPLATE = (
    "QA Automation Engineer / SDET — 4 Years Experience in Test Automation & CI/CD"
)

EMAIL_BODY_TEMPLATE = """\
<p>Dear {role},</p>

<p>
I'm reaching out because I'm interested in QA Automation Engineer / SDET opportunities
{at_company}. With <strong>4 years</strong> of hands-on experience building and scaling
test automation frameworks, I'm confident I can help improve software quality, release
velocity, and test coverage on your team.
</p>

<p><strong>A brief overview of what I bring:</strong></p>
<ul>
  <li><strong>Automation Frameworks:</strong> Playwright, Selenium, and Appium for robust
      end-to-end and cross-platform test suites.</li>
  <li><strong>API &amp; Integration Testing:</strong> Extensive experience validating REST
      APIs with Postman and automated integration checks.</li>
  <li><strong>Test Strategy &amp; Engineering:</strong> Regression suites and release-ready
      test plans that reduced manual effort and improved defect detection.</li>
  <li><strong>CI/CD Integration:</strong> Automated pipelines using Pytest for fast, reliable
      release cycles.</li>
  <li><strong>Cross-Functional Collaboration:</strong> Worked closely with developers,
      product managers, and stakeholders to align QA with product goals.</li>
</ul>

<p>
I've attached my resume for your consideration. I'd welcome the chance to connect for a
brief 15-minute call to discuss how my experience could help your team.
</p>

<p>Thank you for your time{name_suffix}.</p>

<p>
Warm regards,<br>
<strong>Chirag Khanduja</strong><br>
QA Automation Engineer | SDET<br>
903-422-6868
</p>

<p style="font-size:11px;color:#888;margin-top:24px;">
If you'd rather not receive future emails from me, just reply with "unsubscribe" and
I won't contact you again.
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
#  CREDENTIALS — loaded from .env, never hardcoded
# ─────────────────────────────────────────────
def load_credentials() -> Dict[str, str]:
    if not ENV_FILE.exists():
        raise SystemExit(
            f"Missing .env file at {ENV_FILE}\n"
            "Create one with:\n"
            "  EMAIL_ADDRESS=youraddress@gmail.com\n"
            "  EMAIL_PASSWORD=your_app_password\n"
        )
    load_dotenv(ENV_FILE)
    email_addr = os.getenv("EMAIL_ADDRESS")
    email_pass = os.getenv("EMAIL_PASSWORD")
    if not email_addr or not email_pass:
        raise SystemExit("EMAIL_ADDRESS or EMAIL_PASSWORD missing from .env file.")
    return {"address": email_addr, "password": email_pass}


# ─────────────────────────────────────────────
#  EMAIL VALIDATION REGEX
# ─────────────────────────────────────────────
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,7}")


# ─────────────────────────────────────────────
#  RECIPIENT LOADING (CSV with merge fields)
# ─────────────────────────────────────────────
def load_recipients(csv_path: Path) -> List[Dict[str, str]]:
    """
    Expected columns: email (required), first_name, company, role (all optional).
    Returns a list of dicts, one per recipient.
    """
    if not csv_path.exists():
        raise SystemExit(f"Recipients CSV not found: {csv_path}")

    recipients: List[Dict[str, str]] = []
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = [c.strip().lower() for c in (reader.fieldnames or [])]
        if "email" not in fieldnames:
            raise SystemExit("recipients.csv must have an 'email' column.")

        # Build a case-insensitive lookup of actual column names
        col_map = {c.strip().lower(): c for c in (reader.fieldnames or [])}

        for row in reader:
            raw_email = (row.get(col_map["email"], "") or "").strip().lower()
            if not EMAIL_RE.fullmatch(raw_email):
                log.warning("Invalid email skipped: %s", raw_email)
                continue

            domain = raw_email.split("@")[-1]
            if domain in EXCLUDED_DOMAINS or raw_email in EXCLUDED_EMAILS:
                log.debug("Excluded recipient skipped: %s", raw_email)
                continue

            recipients.append({
                "email": raw_email,
                "first_name": (row.get(col_map.get("first_name", ""), "") or "").strip(),
                "company": (row.get(col_map.get("company", ""), "") or "").strip(),
                "role": (row.get(col_map.get("role", ""), "") or "").strip(),
            })

    # Deduplicate by email, preserve order
    seen = set()
    unique = []
    for r in recipients:
        if r["email"] not in seen:
            seen.add(r["email"])
            unique.append(r)

    log.info("Total unique valid recipients loaded: %d", len(unique))
    return unique


def load_already_sent() -> Set[str]:
    if not SENT_LOG_FILE.exists():
        return set()
    with SENT_LOG_FILE.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        return {row[0].strip().lower() for row in reader if row}


def record_sent(email: str) -> None:
    is_new = not SENT_LOG_FILE.exists()
    with SENT_LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["email", "sent_at"])
        writer.writerow([email, date.today().isoformat()])


# ─────────────────────────────────────────────
#  PERSONALIZATION
# ─────────────────────────────────────────────
def personalize(template: str, recipient: Dict[str, str]) -> str:
    first_name = recipient.get("first_name") or ""
    company = recipient.get("company") or ""
    role = recipient.get("role") or "Hiring Manager"

    return template.format(
        first_name=first_name or "there",
        company=company or "your organization",
        role=role,
        at_company=f"at {company}" if company else "at your organization",
        name_suffix=f", {first_name}" if first_name else "",
    )


# ─────────────────────────────────────────────
#  DAILY LOG (how many sent today, across runs)
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
            log.info("Hourly limit reached. Waiting %.0f minutes…", wait_secs / 60)
            time.sleep(wait_secs)
            self.timestamps = []

    def record(self) -> None:
        self.timestamps.append(time.time())


# ─────────────────────────────────────────────
#  SMTP
# ─────────────────────────────────────────────
def build_message(creds: Dict[str, str], to_email: str, subject: str, html_body: str,
                   attachment_data: Optional[bytes], attach_mime: Optional[str],
                   attach_name: Optional[str]) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = creds["address"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.add_alternative(html_body, subtype="html")
    if attachment_data and attach_mime and attach_name:
        maintype, subtype = attach_mime.split("/", 1)
        msg.add_attachment(attachment_data, maintype=maintype,
                            subtype=subtype, filename=attach_name)
    return msg


def _try_starttls(creds: Dict[str, str], timeout: int) -> smtplib.SMTP:
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=timeout)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(creds["address"], creds["password"])
    return server


def _try_ssl(creds: Dict[str, str], timeout: int) -> smtplib.SMTP_SSL:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=timeout)
    server.login(creds["address"], creds["password"])
    return server


def connect_smtp(creds: Dict[str, str]) -> Union[smtplib.SMTP, smtplib.SMTP_SSL]:
    for attempt in range(1, SMTP_MAX_RETRIES + 1):
        try:
            server = _try_starttls(creds, SMTP_TIMEOUT)
            log.info("Connected via 587 (STARTTLS) — attempt %d", attempt)
            return server
        except Exception as exc:
            log.warning("Port 587 failed (%d/%d): %s", attempt, SMTP_MAX_RETRIES, exc)
        try:
            server = _try_ssl(creds, SMTP_TIMEOUT)
            log.info("Connected via 465 (SSL) — attempt %d", attempt)
            return server
        except Exception as exc:
            log.warning("Port 465 failed (%d/%d): %s", attempt, SMTP_MAX_RETRIES, exc)
        if attempt < SMTP_MAX_RETRIES:
            wait = random.uniform(*SMTP_RETRY_WAIT)
            log.info("Retrying in %.0f seconds…", wait)
            time.sleep(wait)
    raise RuntimeError("Cannot connect to Gmail SMTP. Check internet connection / app password.")


# ─────────────────────────────────────────────
#  PROGRESS BAR
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
    creds = load_credentials()

    attach_data = attach_mime = attach_name = None
    if ATTACHMENT_PATH.exists():
        attach_data = ATTACHMENT_PATH.read_bytes()
        attach_mime = mimetypes.guess_type(str(ATTACHMENT_PATH))[0] or "application/octet-stream"
        attach_name = ATTACHMENT_PATH.name
    else:
        log.warning("Attachment not found at %s — emails will be sent WITHOUT attachment.",
                    ATTACHMENT_PATH)

    already_today = get_today_sent_count()
    remaining_cap = DAILY_CAP - already_today
    if remaining_cap <= 0:
        log.info("Daily cap (%d) already reached today. Run again tomorrow.", DAILY_CAP)
        return
    log.info("Daily cap: %d | Already sent today: %d | Remaining: %d",
              DAILY_CAP, already_today, remaining_cap)

    all_recipients = load_recipients(RECIPIENTS_CSV)
    already_sent = load_already_sent()
    fresh_recipients = [r for r in all_recipients if r["email"] not in already_sent]
    skipped = len(all_recipients) - len(fresh_recipients)
    if skipped:
        log.info("Skipping %d recipient(s) already emailed previously.", skipped)

    send_list = fresh_recipients[:remaining_cap]
    log.info("Total emails to send this run: %d", len(send_list))

    if not send_list:
        log.info("No emails to send — script exiting.")
        return

    if DRY_RUN:
        log.info("DRY RUN MODE — no emails will be sent. Preview of first 3:")
        for r in send_list[:3]:
            subject = personalize(EMAIL_SUBJECT_TEMPLATE, r)
            log.info("  → To: %s | Subject: %s", r["email"], subject)
        log.info("Set DRY_RUN = False in the script when ready to actually send.")
        return

    total = len(send_list)
    sent_count = 0
    domain_count: Dict[str, int] = {}
    rate_limiter = HourlyRateLimiter(MAX_PER_HOUR)

    log.info("Starting send: %d emails | Batch size: %d | Max per hour: %d",
              total, BATCH_SIZE, MAX_PER_HOUR)

    server = connect_smtp(creds)

    for i, recipient in enumerate(send_list):
        to_email = recipient["email"]

        if i > 0 and i % BATCH_SIZE == 0:
            pause = random.uniform(*SESSION_BREAK)
            log.info("Batch complete (%d sent). Taking break for %.0f minutes…",
                      sent_count, pause / 60)
            try:
                server.quit()
            except Exception:
                pass
            time.sleep(pause)
            server = connect_smtp(creds)

        rate_limiter.wait_if_needed()

        subject = personalize(EMAIL_SUBJECT_TEMPLATE, recipient)
        body = personalize(EMAIL_BODY_TEMPLATE, recipient)
        msg = build_message(creds, to_email, subject, body, attach_data, attach_mime, attach_name)

        try:
            server.send_message(msg)
            sent_count += 1
            rate_limiter.record()
            record_sent(to_email)
            log.info("Sent [%d/%d] → %s", sent_count, total, to_email)

        except smtplib.SMTPRecipientsRefused:
            log.warning("Refused: %s", to_email)

        except smtplib.SMTPServerDisconnected:
            log.warning("Server disconnected — reconnecting…")
            try:
                server = connect_smtp(creds)
                server.send_message(msg)
                sent_count += 1
                rate_limiter.record()
                record_sent(to_email)
                log.info("Sent (retry) [%d/%d] → %s", sent_count, total, to_email)
            except Exception as exc:
                log.error("Retry failed %s: %s", to_email, exc)

        except smtplib.SMTPException as exc:
            log.error("SMTP error %s: %s", to_email, exc)

        except Exception as exc:
            log.error("Unexpected error %s: %s", to_email, exc)

        simple_bar(sent_count, total)

        domain = to_email.split("@")[-1]
        domain_count[domain] = domain_count.get(domain, 0) + 1
        if domain_count[domain] % DOMAIN_BURST_SIZE == 0:
            time.sleep(random.uniform(*DOMAIN_BURST_PAUSE))

        time.sleep(random.uniform(*PER_EMAIL_DELAY))

    print()
    try:
        server.quit()
    except Exception:
        pass

    update_daily_log(sent_count)
    log.info("Complete — sent %d/%d emails.", sent_count, total)


if __name__ == "__main__":
    main()