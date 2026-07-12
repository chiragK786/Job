#!/usr/bin/env python3
"""
MANUAL EMAIL SENDER
- Recipients: either paste them directly into MANUAL_EMAILS below, OR point
  MANUAL_EMAILS_CSV at a CSV file with an "Email" column (or no header —
  first column is used).
- Connects via port 587 (STARTTLS) first, falls back to 465 (SSL), with
  a few retries if the connection is flaky.
- Keeps a simple daily send cap and a dedup log so you don't accidentally
  email the same person twice across runs.

WHAT'S DELIBERATELY LEFT OUT vs. more "aggressive" versions of this script:
- No batching / long session-break / hourly-limiter machinery designed to
  sustain hundreds of sends a day while dodging Gmail's spam detection.
  If you're only sending a personal, curated list of outreach emails, you
  don't need that -- and if you need it to hit big daily volumes, that's
  bulk/spam territory I'd rather not help optimize.
- Credentials are never hard-coded with real values in this file; fill
  them in yourself, and prefer an environment variable if you can.

HOW TO USE
1. Add your emails to MANUAL_EMAILS below, or set MANUAL_EMAILS_CSV to a
   CSV file path (one "Email" column, or just one column of addresses).
2. Fill in EMAIL_ADDRESS, EMAIL_PASSWORD (a Gmail App Password, not your
   real password), and ATTACHMENT_PATH.
3. Run with DRY_RUN=True first to check the recipient list, then set it
   to False to actually send.
"""

import csv
import logging
import mimetypes
import random
import re
import smtplib
import time
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, List, Set, Union

# ─────────────────────────────────────────────
#  ✅ ADD YOUR EMAILS HERE (manual list)
# ─────────────────────────────────────────────
MANUAL_EMAILS: List[str] = ["h.salama@minds_pool.com","Sunil.b@dprsolutionsinc.com","recruitment@atdrive.com"
    # "hr@company1.com",
    # "recruiter@company2.com",
]

# ─────────────────────────────────────────────
#  ✅ OR LOAD FROM A CSV FILE
#  CSV can have a header called "Email" (any case), or no header at all
#  (first column is treated as the email).
# ─────────────────────────────────────────────
MANUAL_EMAILS_CSV: str = ""   # e.g. "recipients.csv" — leave blank to skip

# ─────────────────────────────────────────────
#  CONFIG — fill these in yourself
# ─────────────────────────────────────────────
ATTACHMENT_PATH = (
    "/Users/chiragkhanduja/PycharmProjects/PythonProject11/"
    "Kanishkakohli_Resume (2).pdf"
)

EMAIL_ADDRESS  = "kanishkakohli4@gmail.com"
EMAIL_PASSWORD = "vyof doas bgra mbvh"   # Gmail App Password

BASE_DIR         = Path(__file__).resolve().parent
SENT_EMAILS_FILE = BASE_DIR / "sent_emails_k1.csv"
DAILY_LOG_FILE   = BASE_DIR / "daily_log_k1.csv"
APP_LOG_FILE     = BASE_DIR / "app_k_1.log"

EXCLUDED_DOMAINS: Set[str] = {
    "squareboat.com",
    "hudle.in",
    "infosys.com",
    "cgi.com",
    "rayosys.com",
    "cognizant.com",
    "herovired.com",
    "raftlabs.co",
    "grappus.com",
    "primathon.in",
    "squareops.com",
    "wizzybox.com",
    "bonami.in",
    "locofast.com",
    "legistify.com",
    "pushowl.com",
    "idreamcareer.com",
    "venturasecurities.com",
    "scuderia.in",
    "questt.com",
    "ongrid.in",
    "tradingwithvivek.com",
    "earthclock.in",
    "dronamaps.com",
    "sparkeighteen.com",
    "embglobal.com",
    "dotpe.in",
    "programming.com",
}
EXCLUDED_EMAILS: Set[str] = {"info@jobcurator.in"}

DRY_RUN = False          # keep True until you've checked the recipient list
DAILY_CAP = 40          # sane number for genuine, personal outreach
DELAY_SECONDS = (5, 12) # polite pause between individual sends

SMTP_TIMEOUT = 30
SMTP_MAX_RETRIES = 3
SMTP_RETRY_WAIT = (10, 20)

# ─────────────────────────────────────────────
#  EMAIL CONTENT
# ─────────────────────────────────────────────
EMAIL_SUBJECT = "Exploring Opportunities | [Your Role] – [X Years Experience]"

EMAIL_BODY = """\
<p>Dear Hiring Manager,</p>

<p>
I am writing to express my interest in an opportunity within your organization.
</p>

<p>
I have attached my resume for your consideration and would welcome the chance
to connect for a brief conversation.
</p>

<p>Thank you for your time and consideration.</p>

<p>
Best regards,<br>
[Your Name]<br>
[Your Phone]
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

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,7}")

# ─────────────────────────────────────────────
#  EMAIL LOADING — manual list + optional CSV
# ─────────────────────────────────────────────
def load_manual_emails() -> List[str]:
    emails: List[str] = []

    for e in MANUAL_EMAILS:
        e = e.strip().lower()
        if EMAIL_RE.fullmatch(e):
            emails.append(e)
        elif e:
            log.warning("Invalid email skipped: %s", e)

    if MANUAL_EMAILS_CSV:
        csv_path = Path(MANUAL_EMAILS_CSV)
        if not csv_path.exists():
            log.error("CSV file not found: %s", MANUAL_EMAILS_CSV)
        else:
            with csv_path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                col = next(
                    (c for c in (reader.fieldnames or []) if c.strip().lower() == "email"),
                    None,
                )
                if col is None:
                    f.seek(0)
                    for row in csv.reader(f):
                        if row:
                            e = row[0].strip().lower()
                            if EMAIL_RE.fullmatch(e):
                                emails.append(e)
                else:
                    for row in reader:
                        e = (row[col] or "").strip().lower()
                        if EMAIL_RE.fullmatch(e):
                            emails.append(e)
                        elif e:
                            log.warning("Invalid email in CSV skipped: %s", e)
            log.info("Loaded from CSV: %s", csv_path.name)

    filtered = []
    for e in emails:
        domain = e.split("@")[-1]
        if domain in EXCLUDED_DOMAINS or e in EXCLUDED_EMAILS:
            log.debug("Excluded: %s", e)
        else:
            filtered.append(e)

    seen: Set[str] = set()
    unique = []
    for e in filtered:
        if e not in seen:
            seen.add(e)
            unique.append(e)

    log.info("Total unique valid emails loaded: %d", len(unique))
    return unique

# ─────────────────────────────────────────────
#  DEDUP / DAILY LOG
# ─────────────────────────────────────────────
def load_sent_emails() -> Set[str]:
    if not SENT_EMAILS_FILE.exists():
        return set()
    with SENT_EMAILS_FILE.open(newline="") as f:
        return {row[0].strip().lower() for row in csv.reader(f) if row}

def mark_sent(email: str) -> None:
    with SENT_EMAILS_FILE.open("a", newline="") as f:
        csv.writer(f).writerow([email])

def get_today_sent_count() -> int:
    today = date.today().isoformat()
    if not DAILY_LOG_FILE.exists():
        return 0
    with DAILY_LOG_FILE.open(newline="") as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if row and row[0] == today:
            return int(row[1])
    return 0

def update_daily_log(count: int) -> None:
    today = date.today().isoformat()
    rows: List[List[str]] = [["Date", "Count"]]
    if DAILY_LOG_FILE.exists():
        with DAILY_LOG_FILE.open(newline="") as f:
            rows = list(csv.reader(f))
    updated = False
    for row in rows[1:]:
        if row and row[0] == today:
            row[1] = str(int(row[1]) + count)
            updated = True
            break
    if not updated:
        rows.append([today, str(count)])
    with DAILY_LOG_FILE.open("w", newline="") as f:
        csv.writer(f).writerows(rows)

# ─────────────────────────────────────────────
#  SMTP — 587 (STARTTLS) primary, 465 (SSL) fallback, with retries
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
    server.ehlo()
    server.starttls()
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
            log.info("Connected via 587 (STARTTLS) — attempt %d", attempt)
            return server
        except Exception as exc:
            log.warning("Port 587 failed (%d/%d): %s", attempt, SMTP_MAX_RETRIES, exc)
        try:
            server = _try_ssl(SMTP_TIMEOUT)
            log.info("Connected via 465 (SSL) — attempt %d", attempt)
            return server
        except Exception as exc:
            log.warning("Port 465 failed (%d/%d): %s", attempt, SMTP_MAX_RETRIES, exc)
        if attempt < SMTP_MAX_RETRIES:
            wait = random.uniform(*SMTP_RETRY_WAIT)
            log.info("Retrying in %.0f seconds…", wait)
            time.sleep(wait)
    raise RuntimeError("Could not connect to Gmail SMTP. Check internet/firewall settings.")

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
        raise FileNotFoundError(f"Attachment not found: {attach_path}")

    already_today = get_today_sent_count()
    remaining_cap = DAILY_CAP - already_today
    if remaining_cap <= 0:
        log.info("Daily cap (%d) already reached today. Run again tomorrow.", DAILY_CAP)
        return
    log.info("Daily cap: %d | Sent today: %d | Remaining: %d",
             DAILY_CAP, already_today, remaining_cap)

    all_emails = load_manual_emails()
    sent_before = load_sent_emails()
    send_list = [e for e in all_emails if e not in sent_before][:remaining_cap]

    log.info("New recipients to send today: %d", len(send_list))
    if not send_list:
        log.info("Nothing to send — exiting.")
        return

    if DRY_RUN:
        log.info("DRY RUN — no emails sent. Recipients:")
        for e in send_list:
            log.info("  -> %s", e)
        log.info("Set DRY_RUN=False to actually send.")
        return

    attach_data = attach_path.read_bytes()
    attach_mime = mimetypes.guess_type(str(attach_path))[0] or "application/octet-stream"
    attach_name = attach_path.name

    total = len(send_list)
    sent_count = 0

    server = connect_smtp()

    for i, to_email in enumerate(send_list, 1):
        msg = build_message(to_email, attach_data, attach_mime, attach_name)
        try:
            server.send_message(msg)
            sent_count += 1
            mark_sent(to_email)
            log.info("[%d/%d] Sent -> %s", i, total, to_email)
        except smtplib.SMTPRecipientsRefused:
            log.warning("[%d/%d] Refused: %s", i, total, to_email)
        except smtplib.SMTPServerDisconnected:
            log.warning("Server disconnected — reconnecting…")
            try:
                server = connect_smtp()
                server.send_message(msg)
                sent_count += 1
                mark_sent(to_email)
                log.info("[%d/%d] Sent (retry) -> %s", i, total, to_email)
            except Exception as exc:
                log.error("Retry failed for %s: %s", to_email, exc)
        except smtplib.SMTPException as exc:
            log.error("SMTP error for %s: %s", to_email, exc)
        except Exception as exc:
            log.error("Unexpected error for %s: %s", to_email, exc)

        simple_bar(sent_count, total)
        time.sleep(random.uniform(*DELAY_SECONDS))

    print()
    try:
        server.quit()
    except Exception:
        pass

    update_daily_log(sent_count)
    log.info("Done — sent %d/%d emails today.", sent_count, total)

if __name__ == "__main__":
    main()