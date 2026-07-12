#!/usr/bin/env python3
"""
OPTIMISED MULTI-PDF EMAIL SENDER v2
- 200+ emails/day without Gmail block
- Smart batching: 40 emails per SMTP session
- Long session breaks (20-35 min) between batches
- Faster per-email delay (3-7 sec)
- Hourly rate limiter (max 35/hour)
- Warm-up mode for new accounts
- Resumes automatically after breaks
- All original features retained
"""

import re
import csv
import os
import time
import random
import mimetypes
import smtplib
import logging
import pdfplumber
from email.message import EmailMessage
from datetime import date, datetime
from pathlib import Path
from typing import Set, List, Dict

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
PDF_PATHS: List[str] = [
    "/Users/chiragkhanduja/PycharmProjects/PythonProject11/NCR_Noida_Delhi_Gurgaon (17).pdf",
]

ATTACHMENT_PATH = (
    "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Sarita Kumari_Senior QA Engineer.pdf"
)

EMAIL_ADDRESS  = "saritac0111@gmail.com"
EMAIL_PASSWORD = "zack jchz kxag mxwp"

BASE_DIR           = Path("/Users/chiragkhanduja/PycharmProjects/PythonProject11")
SENT_EMAILS_FILE   = BASE_DIR / "sent_emails_s.csv"
LOG_FILE           = BASE_DIR / "email_log_s.csv"
PREVIEW_CSV        = BASE_DIR / "preview_recipients_s.csv"
APP_LOG_FILE       = BASE_DIR / "app_s.log"

EXCLUDED_DOMAINS: Set[str] = {
    "squareboat.com", "hudle.in", "infosys.com",
    "cgi.com", "rayosys.com", "cognizant.com",
}

EXCLUDED_EMAILS: Set[str] = {"info@jobcurator.in"}

DRY_RUN = False

# ─────────────────────────────────────────────
#  ANTI-BLOCK / RATE LIMITING
# ─────────────────────────────────────────────
PER_EMAIL_DELAY    = (3, 7)
DOMAIN_BURST_SIZE  = 2
DOMAIN_BURST_PAUSE = (15, 30)
BATCH_SIZE         = 40
SESSION_BREAK      = (600, 1200)   # 10–20 min
MAX_PER_HOUR       = 55
DAILY_CAP          = 250
WARMUP_MODE        = False
WARMUP_DAILY_CAP   = 50
WARMUP_DELAY       = (8, 15)

# ─────────────────────────────────────────────
#  EMAIL CONTENT
# ─────────────────────────────────────────────
EMAIL_SUBJECT = (
    "QA Engineer — 8.5 Years Experience | Selenium, Java, API Testing | Immediate Joiner"
)

EMAIL_BODY = """\
<p>Dear Hiring Manager,</p>

<p>
I am writing to express my interest in a <strong>QA Engineer</strong> opportunity at your
organization. With <strong>8.5 years of total experience</strong>, including
<strong>6+ years in Quality Assurance</strong>, I bring a strong blend of
<strong>Manual Testing</strong> and <strong>Test Automation</strong> expertise that drives
measurable improvements in software quality and release confidence.
</p>

<p><strong>Here is a snapshot of my profile:</strong></p>
<ul>
  <li>
    <strong>Automation Testing:</strong> Hands-on experience with
    <strong>Selenium WebDriver with Java</strong>, using frameworks such as
    <strong>TestNG</strong>, <strong>Maven</strong>, and
    <strong>Page Object Model (POM)</strong> to build maintainable, scalable test suites.
  </li>
  <li>
    <strong>API Testing:</strong> Proficient in <strong>REST API testing</strong>
    using <strong>Postman</strong> and <strong>Rest Assured</strong> for end-to-end
    service validation and integration checks.
  </li>
  <li>
    <strong>Manual &amp; Functional Testing:</strong> Deep expertise in
    <strong>Functional Testing</strong>, <strong>Regression Testing</strong>, and
    managing complete test cycles from requirement analysis to sign-off.
  </li>
  <li>
    <strong>Mobile Testing:</strong> Experienced in mobile application testing using
    <strong>Android Studio</strong> and <strong>BrowserStack</strong> for
    cross-platform and cross-browser validation.
  </li>
  <li>
    <strong>Bug Tracking &amp; Collaboration:</strong> Skilled in <strong>Jira</strong>
    and <strong>Confluence</strong> for defect lifecycle management and cross-functional
    team collaboration.
  </li>
  <li>
    <strong>Debugging &amp; Network Analysis:</strong> Proficient with
    <strong>Charles Proxy</strong> for request interception, traffic analysis,
    and root-cause investigation of defects.
  </li>
  <li>
    <strong>Database Testing:</strong> Working knowledge of <strong>MySQL</strong>
    for backend validation, data integrity checks, and query-based testing.
  </li>
</ul>

<p>
I hold a certification in <strong>Manual &amp; Automation Testing (Selenium with Java)</strong>
and have a consistent track record of improving defect detection rates, reducing manual testing
effort, and collaborating effectively with developers, product managers, and stakeholders.
</p>

<p>
I am currently based in <strong>New Delhi</strong> and am available as an
<strong>Immediate Joiner</strong>.
</p>

<p>
I have attached my updated resume for your consideration. I would welcome a brief call to
discuss how my experience aligns with your team's needs.
</p>

<p>Thank you for your time. I look forward to hearing from you.</p>

<p>
Warm regards,<br>
<strong>Sarita Kumari</strong><br>
QA Engineer | Manual &amp; Automation Testing<br>
7200979238
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
            log.info(
                "⏳ Hourly limit (%d/hr) reached. Waiting %.0f minutes…",
                self.max_per_hour, wait_secs / 60
            )
            time.sleep(wait_secs)
            self.timestamps = []

    def record(self) -> None:
        self.timestamps.append(time.time())

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
#  EMAIL EXTRACTION
# ─────────────────────────────────────────────
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,7}")

def extract_emails_from_pdfs(pdf_paths: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
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
                    domain = email.split("@")[-1]
                    if domain in EXCLUDED_DOMAINS:
                        continue
                    if email in EXCLUDED_EMAILS:
                        continue
                    counts[email] = counts.get(email, 0) + 1
    log.info("Unique emails found across all PDFs: %d", len(counts))
    return counts

# ─────────────────────────────────────────────
#  SMTP HELPERS
# ─────────────────────────────────────────────
def build_message(to_email: str, attachment_data: bytes,
                  attach_mime: str, attach_name: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"]    = EMAIL_ADDRESS
    msg["To"]      = to_email
    msg["Subject"] = EMAIL_SUBJECT
    msg.add_alternative(EMAIL_BODY, subtype="html")
    maintype, subtype = attach_mime.split("/", 1)
    msg.add_attachment(attachment_data, maintype=maintype,
                       subtype=subtype, filename=attach_name)
    return msg

def connect_smtp() -> smtplib.SMTP_SSL:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    log.info("✅ SMTP connected")
    return server

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

    effective_daily_cap   = WARMUP_DAILY_CAP if WARMUP_MODE else DAILY_CAP
    effective_email_delay = WARMUP_DELAY      if WARMUP_MODE else PER_EMAIL_DELAY

    if WARMUP_MODE:
        log.info("🔥 WARM-UP MODE active — max %d emails today, slower delays", WARMUP_DAILY_CAP)

    already_today = get_today_sent_count()
    remaining_cap = effective_daily_cap - already_today
    if remaining_cap <= 0:
        log.info("📅 Daily cap of %d already reached today. Run again tomorrow.", effective_daily_cap)
        return
    log.info("📅 Daily cap: %d | Sent today: %d | Remaining: %d",
             effective_daily_cap, already_today, remaining_cap)

    all_emails  = extract_emails_from_pdfs(PDF_PATHS)
    sent_before = load_sent_emails()
    send_list   = sorted(e for e in all_emails if e not in sent_before)
    send_list   = send_list[:remaining_cap]

    log.info("Already sent (all time): %d  |  New to send today: %d",
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

    total         = len(send_list)
    sent_count    = 0
    domain_count: Dict[str, int] = {}
    rate_limiter  = HourlyRateLimiter(MAX_PER_HOUR)

    log.info("🚀 Starting send: %d emails | Batch size: %d | Max/hour: %d",
             total, BATCH_SIZE, MAX_PER_HOUR)

    server = connect_smtp()

    if RICH:
        progress = make_progress()
        progress.start()
        task = progress.add_task("send", total=total)

    for i, to_email in enumerate(send_list):

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
            server = connect_smtp()
            if RICH:
                progress = make_progress()
                progress.start()
                task = progress.add_task("send", total=total)

        rate_limiter.wait_if_needed()

        msg = build_message(to_email, attach_data, attach_mime, attach_name)
        try:
            server.send_message(msg)
            sent_count += 1
            rate_limiter.record()
            mark_sent(to_email)
            log.info("✔ [%d/%d] Sent → %s", sent_count, total, to_email)
        except smtplib.SMTPRecipientsRefused:
            log.warning("✘ Refused: %s", to_email)
        except smtplib.SMTPServerDisconnected:
            log.warning("🔌 Server disconnected — reconnecting…")
            try:
                server = connect_smtp()
                server.send_message(msg)
                sent_count += 1
                rate_limiter.record()
                mark_sent(to_email)
                log.info("✔ [%d/%d] Sent (retry) → %s", sent_count, total, to_email)
            except Exception as exc:
                log.error("✘ Retry failed for %s: %s", to_email, exc)
        except smtplib.SMTPException as exc:
            log.error("✘ SMTP error for %s: %s", to_email, exc)
        except Exception as exc:
            log.error("✘ Unexpected error for %s: %s", to_email, exc)

        if RICH:
            progress.update(task, advance=1)
        else:
            simple_bar(sent_count, total)

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
    log.info("🎉 Done — %d/%d emails sent today.", sent_count, total)
    log.info("📊 Total sent all time: %d", len(load_sent_emails()))

    delete_pdfs(PDF_PATHS, sent_count, total)

if __name__ == "__main__":
    main()