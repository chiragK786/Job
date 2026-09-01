#!/usr/bin/env python3
"""
OPTIMISED MULTI-PDF EMAIL SENDER v4
- Dual Gmail account with auto-fallback on limit/block
- Reply-To set to secondary account
- Port 587 (STARTTLS) primary, 465 (SSL) fallback
- 30-second connection timeout
- Auto-retry connect up to 3 times
- Smart batching: 50 emails per SMTP session
- Long session breaks (20-35 min) between batches
- Warm-up mode for new accounts
- Resumes automatically after breaks
- IMAP bounce detection: skips "Address not found" emails
"""

import re
import csv
import os
import time
import random
import mimetypes
import smtplib
imaplib = __import__("imaplib")
import email as email_lib
import logging
import pdfplumber
from email.message import EmailMessage
from datetime import date
from pathlib import Path
from typing import Set, List, Dict, Union, Tuple

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
PDF_PATHS: List[str] = [
    "/Users/chiragkhanduja/Downloads/Testing Jobs Full List (2).pdf",
]

ATTACHMENT_PATH = (
    "/Users/chiragkhanduja/PycharmProjects/PythonProject11/"
    "Chirag_Khanduja_AITester_SDET_QA_Engineer.pdf"
)

# ── Accounts — primary first, fallback second ──
ACCOUNTS = [
    {"email": "chiragkhanduja786@gmail.com",  "password": "ivci swwm gwfx btku"},
    {"email": "chiragkhanduja034@gmail.com",  "password": "htda ohsb jgnx mabb"},
]

REPLY_TO = "chiragkhanduja786@gmail.com"

BASE_DIR           = Path("/Users/chiragkhanduja/PycharmProjects/PythonProject11")
SENT_EMAILS_FILE   = BASE_DIR / "sent_emails.csv"
LOG_FILE           = BASE_DIR / "email_log.csv"
PREVIEW_CSV        = BASE_DIR / "preview_recipients.csv"
APP_LOG_FILE       = BASE_DIR / "app.log"

EXCLUDED_DOMAINS: Set[str] = {
    "squareboat.com", "hudle.in", "programming.com"
}

EXCLUDED_EMAILS: Set[str] = {"info@jobcurator.in"}

DRY_RUN = False

# ─────────────────────────────────────────────
#  SMTP CONNECTION SETTINGS
# ─────────────────────────────────────────────
SMTP_TIMEOUT     = 30
SMTP_MAX_RETRIES = 3
SMTP_RETRY_WAIT  = (10, 20)

# ─────────────────────────────────────────────
#  ANTI-BLOCK / RATE LIMITING
# ─────────────────────────────────────────────
PER_EMAIL_DELAY    = (3, 7)
DOMAIN_BURST_SIZE  = 2
DOMAIN_BURST_PAUSE = (15, 30)
BATCH_SIZE         = 50
SESSION_BREAK      = (600, 1200)   # 20–35 min between batches
WARMUP_MODE        = False
WARMUP_DELAY       = (8, 15)

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
#  LOGGING SETUP
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
#  SENT-EMAIL TRACKING
# ─────────────────────────────────────────────
def load_sent_emails() -> Set[str]:
    if not SENT_EMAILS_FILE.exists():
        return set()
    with SENT_EMAILS_FILE.open(newline="") as f:
        return {row[0].strip().lower() for row in csv.reader(f) if row}

def mark_sent(email: str) -> None:
    SENT_EMAILS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SENT_EMAILS_FILE.open("a", newline="") as f:
        csv.writer(f).writerow([email])

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
#  EMAIL EXTRACTION
# ─────────────────────────────────────────────
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,7}")

def is_valid_email(email: str) -> bool:
    """Sanity checks to reject malformed emails like -anshu@domain.com"""
    try:
        local, domain = email.rsplit("@", 1)
    except ValueError:
        return False
    if local.startswith(("-", ".", "_", "+")) or local.endswith(("-", ".", "_", "+")):
        return False
    if ".." in email:
        return False
    if len(local) < 1:
        return False
    if "." not in domain or domain.startswith("-") or domain.endswith("-"):
        return False
    return True

def extract_emails_from_pdfs(pdf_paths: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    skipped = 0
    for path_str in pdf_paths:
        path = Path(path_str)
        if not path.exists():
            log.warning("Missing PDF: %s", path)
            continue
        log.info("Reading PDF: %s", path.name)
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for match in EMAIL_RE.findall(text):
                    email = match.lower().strip()
                    if not is_valid_email(email):
                        log.debug("Skipped invalid email: %s", email)
                        skipped += 1
                        continue
                    domain = email.split("@")[-1]
                    if domain in EXCLUDED_DOMAINS:
                        continue
                    if email in EXCLUDED_EMAILS:
                        continue
                    counts[email] = counts.get(email, 0) + 1
    log.info("Unique valid emails found: %d  |  Skipped invalid: %d", len(counts), skipped)
    return counts


# ─────────────────────────────────────────────
#  BOUNCE DETECTION (IMAP)
# ─────────────────────────────────────────────
BOUNCE_SENDERS = {
    "mailer-daemon@googlemail.com",
    "mailer-daemon@gmail.com",
    "postmaster@gmail.com",
}
BOUNCE_SUBJECTS = [
    "address not found",
    "delivery status notification",
    "undelivered mail returned",
    "mail delivery failed",
    "failure notice",
    "returned mail",
]

def fetch_bounced_emails(account: dict) -> Set[str]:
    """
    Connect to Gmail IMAP, scan inbox for bounce/NDR emails,
    extract the original recipient addresses and return them.
    """
    bounced: Set[str] = set()
    EMAIL_IN_BODY = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,7}")
    try:
        log.info("📬 Checking inbox for bounces via IMAP (%s)…", account["email"])
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(account["email"], account["password"])
        mail.select("inbox")

        # Search for emails from mailer-daemon
        for sender in BOUNCE_SENDERS:
            _, data = mail.search(None, f'FROM "{sender}"')
            ids = data[0].split()
            for num in ids:
                _, msg_data = mail.fetch(num, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)
                subject = (msg.get("Subject") or "").lower()

                # Only process if subject looks like a bounce
                if not any(kw in subject for kw in BOUNCE_SUBJECTS):
                    continue

                # Extract emails from body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        ct = part.get_content_type()
                        if ct in ("text/plain", "text/html"):
                            try:
                                body += part.get_payload(decode=True).decode(errors="ignore")
                            except Exception:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    except Exception:
                        pass

                found = EMAIL_IN_BODY.findall(body)
                for addr in found:
                    addr = addr.lower().strip()
                    # Skip daemon/system addresses
                    if any(d in addr for d in ["mailer-daemon", "googlemail", "gmail.com", "google.com"]):
                        continue
                    bounced.add(addr)

        mail.logout()
        log.info("📭 Bounce check done — %d bounced address(es) found.", len(bounced))
    except Exception as exc:
        log.warning("⚠️  IMAP bounce check failed (non-critical): %s", exc)
    return bounced

def mark_bounced(emails: Set[str]) -> None:
    """Add bounced emails to sent list so they are never retried."""
    if not emails:
        return
    existing = load_sent_emails()
    new_bounced = emails - existing
    if not new_bounced:
        return
    SENT_EMAILS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SENT_EMAILS_FILE.open("a", newline="") as f:
        writer = csv.writer(f)
        for addr in new_bounced:
            writer.writerow([addr])
    log.info("🚫 Marked %d bounced email(s) as do-not-send.", len(new_bounced))

# ─────────────────────────────────────────────
#  SMTP HELPERS
# ─────────────────────────────────────────────
def build_message(to_email: str, from_email: str,
                  attachment_data: bytes,
                  attach_mime: str, attach_name: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"]     = from_email
    msg["To"]       = to_email
    msg["Reply-To"] = REPLY_TO
    msg["Subject"]  = EMAIL_SUBJECT
    msg.add_alternative(EMAIL_BODY, subtype="html")
    maintype, subtype = attach_mime.split("/", 1)
    msg.add_attachment(attachment_data, maintype=maintype,
                       subtype=subtype, filename=attach_name)
    return msg


def _try_starttls(email: str, password: str, timeout: int) -> smtplib.SMTP:
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=timeout)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(email, password)
    return server


def _try_ssl(email: str, password: str, timeout: int) -> smtplib.SMTP_SSL:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=timeout)
    server.login(email, password)
    return server


def connect_smtp(account: dict) -> Union[smtplib.SMTP, smtplib.SMTP_SSL]:
    """Connect using the given account dict {email, password}."""
    email, password = account["email"], account["password"]
    for attempt in range(1, SMTP_MAX_RETRIES + 1):
        try:
            server = _try_starttls(email, password, SMTP_TIMEOUT)
            log.info("✅ Connected via 587 (STARTTLS) as %s — attempt %d", email, attempt)
            return server
        except (TimeoutError, OSError, smtplib.SMTPException) as exc:
            log.warning("⚠️  Port 587 failed (%s, attempt %d/%d): %s", email, attempt, SMTP_MAX_RETRIES, exc)

        try:
            server = _try_ssl(email, password, SMTP_TIMEOUT)
            log.info("✅ Connected via 465 (SSL) as %s — attempt %d", email, attempt)
            return server
        except (TimeoutError, OSError, smtplib.SMTPException) as exc:
            log.warning("⚠️  Port 465 failed (%s, attempt %d/%d): %s", email, attempt, SMTP_MAX_RETRIES, exc)

        if attempt < SMTP_MAX_RETRIES:
            wait = random.uniform(*SMTP_RETRY_WAIT)
            log.info("🔄 Retrying in %.0f seconds…", wait)
            time.sleep(wait)

    raise RuntimeError(f"❌ Could not connect with account: {email}")


def connect_smtp_with_fallback(current_index: int) -> Tuple[Union[smtplib.SMTP, smtplib.SMTP_SSL], int]:
    """
    Try to connect starting from current_index.
    Returns (server, account_index_used).
    Raises RuntimeError if all accounts exhausted.
    """
    for idx in range(current_index, len(ACCOUNTS)):
        try:
            server = connect_smtp(ACCOUNTS[idx])
            return server, idx
        except RuntimeError:
            log.warning("⚠️  Account %s exhausted, trying next…", ACCOUNTS[idx]["email"])
    raise RuntimeError("❌ All Gmail accounts exhausted. No more fallback available.")

# ─────────────────────────────────────────────
#  PROGRESS BAR
# ─────────────────────────────────────────────
try:
    from rich.progress import (
        Progress, BarColumn, TimeElapsedColumn,
        TimeRemainingColumn, TextColumn, MofNCompleteColumn,
    )
    RICH = True
except ImportError:
    RICH = False

def make_progress() -> "Progress":
    from rich.progress import (
        Progress, BarColumn, TimeElapsedColumn,
        TimeRemainingColumn, TextColumn, MofNCompleteColumn,
    )
    return Progress(
        TextColumn("[bold green]Sending"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    )

def simple_bar(done: int, total: int) -> None:
    if total == 0:
        return
    filled = int(done / total * 45)
    bar = "█" * filled + "─" * (45 - filled)
    print(f"\r[{bar}] {done}/{total}", end="", flush=True)

# ─────────────────────────────────────────────
#  PDF DELETION
# ─────────────────────────────────────────────
def delete_pdfs(pdf_paths: List[str], sent_count: int, total: int) -> None:
    if sent_count != total:
        log.warning("Skipping PDF deletion — only %d/%d emails sent.", sent_count, total)
        return
    log.info("All emails sent. Deleting source PDF(s)…")
    for path_str in pdf_paths:
        pdf_path = Path(path_str)
        try:
            if pdf_path.exists():
                pdf_path.unlink()
                log.info("🗑  Deleted PDF: %s", pdf_path.name)
        except Exception as exc:
            log.error("Failed to delete %s: %s", pdf_path.name, exc)

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main() -> None:
    attach_path = Path(ATTACHMENT_PATH)
    if not attach_path.exists():
        raise FileNotFoundError(f"Resume not found: {attach_path}")

    # ── Bounce detection: mark bad addresses before sending ────────
    for acc in ACCOUNTS:
        bounced = fetch_bounced_emails(acc)
        mark_bounced(bounced)

    effective_email_delay = WARMUP_DELAY if WARMUP_MODE else PER_EMAIL_DELAY

    if WARMUP_MODE:
        log.info("🔥 WARM-UP MODE active — slower delays")

    all_emails  = extract_emails_from_pdfs(PDF_PATHS)
    sent_before = load_sent_emails()
    send_list   = sorted(e for e in all_emails if e not in sent_before)

    log.info("Already sent (all time): %d  |  New to send: %d",
             len(sent_before), len(send_list))

    if not send_list:
        log.info("No new recipients — nothing to do.")
        return

    if DRY_RUN:
        log.info("DRY RUN — writing preview to %s", PREVIEW_CSV)
        with PREVIEW_CSV.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Email", "Occurrences"])
            for e in send_list:
                writer.writerow([e, all_emails[e]])
        log.info("Preview written (%d rows). Set DRY_RUN=False to send.", len(send_list))
        return

    attach_data = attach_path.read_bytes()
    attach_mime = mimetypes.guess_type(str(attach_path))[0] or "application/octet-stream"
    attach_name = attach_path.name

    total        = len(send_list)
    sent_count   = 0
    domain_count: Dict[str, int] = {}

    # Start with primary account (index 0)
    account_idx = 0
    server, account_idx = connect_smtp_with_fallback(account_idx)
    current_email = ACCOUNTS[account_idx]["email"]
    log.info("🚀 Starting send: %d emails | Batch: %d | Account: %s",
             total, BATCH_SIZE, current_email)

    if RICH:
        progress = make_progress()
        progress.start()
        task = progress.add_task("send", total=total)

    for i, to_email in enumerate(send_list):

        # ── Batch break ────────────────────────────────────────────────
        if i > 0 and i % BATCH_SIZE == 0:
            if RICH:
                progress.stop()
            pause = random.uniform(*SESSION_BREAK)
            log.info(
                "☕ Batch %d/%d complete (%d sent). Session break: %.0f minutes…",
                i // BATCH_SIZE,
                (total + BATCH_SIZE - 1) // BATCH_SIZE,
                sent_count,
                pause / 60,
            )
            try:
                server.quit()
            except Exception:
                pass
            elapsed = 0
            while elapsed < pause:
                sleep_chunk = min(300, pause - elapsed)
                time.sleep(sleep_chunk)
                elapsed += sleep_chunk
                remaining = pause - elapsed
                if remaining > 0:
                    log.info("⏰ Resuming in %.0f minutes…", remaining / 60)
            server, account_idx = connect_smtp_with_fallback(account_idx)
            current_email = ACCOUNTS[account_idx]["email"]
            if RICH:
                progress = make_progress()
                progress.start()
                task = progress.add_task("send", total=total)

        msg = build_message(to_email, current_email, attach_data, attach_mime, attach_name)
        try:
            server.send_message(msg)
            sent_count += 1
            mark_sent(to_email)
            log.info("✔ [%d/%d] Sent → %s  (via %s)", sent_count, total, to_email, current_email)

        except smtplib.SMTPRecipientsRefused:
            log.warning("✘ Refused: %s", to_email)

        except smtplib.SMTPServerDisconnected:
            log.warning("🔌 Disconnected — reconnecting…")
            try:
                server, account_idx = connect_smtp_with_fallback(account_idx)
                current_email = ACCOUNTS[account_idx]["email"]
                msg = build_message(to_email, current_email, attach_data, attach_mime, attach_name)
                server.send_message(msg)
                sent_count += 1
                mark_sent(to_email)
                log.info("✔ [%d/%d] Sent (retry) → %s  (via %s)", sent_count, total, to_email, current_email)
            except Exception as exc:
                log.error("✘ Retry failed for %s: %s", to_email, exc)

        except smtplib.SMTPException as exc:
            err_str = str(exc).lower()
            # Detect limit-related errors and switch account immediately
            if any(k in err_str for k in ("daily limit", "quota", "too many", "temporarily", "suspended", "rate")):
                log.warning("🚫 Account %s hit a limit: %s — switching account…", current_email, exc)
                try:
                    server.quit()
                except Exception:
                    pass
                account_idx += 1   # move to next account
                try:
                    server, account_idx = connect_smtp_with_fallback(account_idx)
                    current_email = ACCOUNTS[account_idx]["email"]
                    log.info("🔀 Switched to account: %s", current_email)
                    msg = build_message(to_email, current_email, attach_data, attach_mime, attach_name)
                    server.send_message(msg)
                    sent_count += 1
                    mark_sent(to_email)
                    log.info("✔ [%d/%d] Sent (switched) → %s  (via %s)", sent_count, total, to_email, current_email)
                except RuntimeError:
                    log.error("❌ All accounts exhausted. Stopping.")
                    break
                except Exception as exc2:
                    log.error("✘ Failed after switch for %s: %s", to_email, exc2)
            else:
                log.error("✘ SMTP error for %s: %s", to_email, exc)

        except Exception as exc:
            log.error("✘ Unexpected error for %s: %s", to_email, exc)

        if RICH:
            progress.update(task, advance=1)
        else:
            simple_bar(sent_count, total)

        # ── Domain burst pause ─────────────────────────────────────────
        domain = to_email.split("@")[-1]
        domain_count[domain] = domain_count.get(domain, 0) + 1
        if domain_count[domain] % DOMAIN_BURST_SIZE == 0:
            pause = random.uniform(*DOMAIN_BURST_PAUSE)
            log.debug("Domain burst pause (%s): %.1fs", domain, pause)
            time.sleep(pause)

        time.sleep(random.uniform(*effective_email_delay))

    if RICH:
        progress.stop()

    try:
        server.quit()
    except Exception:
        pass

    update_daily_log(sent_count)
    log.info("🎉 Done — %d/%d emails sent.", sent_count, total)
    log.info("📊 Total sent all time: %d", len(load_sent_emails()))

    delete_pdfs(PDF_PATHS, sent_count, total)


if __name__ == "__main__":
    main()