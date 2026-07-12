#!/usr/bin/env python3
"""
OPTIMISED MULTI-PDF EMAIL SENDER v2
- 200+ emails/day without Gmail block
- Smart batching: 40 emails per SMTP session
- Long session breaks (10-20 min) between batches
- Faster per-email delay (3-7 sec)
- Hourly rate limiter (max 55/hour)
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
    "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Hyderabad (40).pdf",  # ← update with your leads PDF path
]

ATTACHMENT_PATH = (
    "/Users/chiragkhanduja/PycharmProjects/PythonProject11/Aakriti_Jain.pdf"  # ← update with your resume path
)

EMAIL_ADDRESS  = "aakritij.official@gmail.com"       # ← your Gmail address
EMAIL_PASSWORD = "bceo rety imyw gbrd"        # ← Gmail App Password (Google Account → Security → App Passwords)

BASE_DIR           = Path("/Users/chiragkhanduja/PycharmProjects/PythonProject11")    # ← update base dir
SENT_EMAILS_FILE   = BASE_DIR / "sent_emails_J.csv"
LOG_FILE           = BASE_DIR / "email_log_j.csv"
PREVIEW_CSV        = BASE_DIR / "preview_recipients_j.csv"
APP_LOG_FILE       = BASE_DIR / "app_j.log"

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
    "Product Designer / UI-UX Lead — 7+ Years | SaaS, B2C, B2B, Mobile | Open to Opportunities"
)

EMAIL_BODY = """\
<p>Dear Hiring Manager,</p>

<p>
I hope you are doing well. I am reaching out to express my interest in
<strong>Product Design</strong> and <strong>UI/UX Leadership</strong> opportunities at your
organization. With <strong>7+ years of experience</strong> in end-to-end product design, I have
led design initiatives across <strong>B2C</strong>, <strong>B2B</strong>, and
<strong>SaaS</strong> products — spanning <strong>mobile apps</strong>,
<strong>dashboards</strong>, and <strong>responsive web platforms</strong>.
</p>

<p><strong>Brands and organizations I have worked with include:</strong></p>
<p style="margin: 0 0 1rem; padding-left: 1rem; color: #444;">
Dr. Reddy's Laboratories &nbsp;·&nbsp; Blue Tokai &nbsp;·&nbsp; Nalanda Learning
&nbsp;·&nbsp; Pushowl &nbsp;·&nbsp; Hudle Sports &nbsp;·&nbsp; Awfis &nbsp;·&nbsp;
Grayporter &nbsp;·&nbsp; A91 Partners &nbsp;·&nbsp; Jamboree Education
&nbsp;·&nbsp; Edunext &nbsp;·&nbsp; IBM (Mercedes-Benz R&amp;D)
</p>

<p><strong>Here is a snapshot of what I bring to the role:</strong></p>
<ul>
  <li>
    <strong>UX Strategy &amp; Product Thinking:</strong> Extensive experience translating
    complex business requirements into intuitive, user-centered design solutions with a
    strong focus on <strong>information architecture</strong>, <strong>user flows</strong>,
    and <strong>interaction design</strong>.
  </li>
  <li>
    <strong>Design Systems:</strong> Built and maintained scalable
    <strong>design systems</strong> that improve consistency, accelerate development
    handoff, and align cross-functional teams.
  </li>
  <li>
    <strong>AI-Assisted Design Workflows:</strong> Actively integrating
    <strong>AI-assisted workflows</strong> into the design process to improve efficiency
    and prototype fidelity.
  </li>
  <li>
    <strong>Mobile &amp; Web Product Design:</strong> Delivered polished, high-fidelity
    <strong>UI/UX designs</strong> for <strong>iOS</strong>, <strong>Android</strong>,
    and responsive web across diverse industries including edtech, healthtech,
    fintech, and consumer apps.
  </li>
  <li>
    <strong>Cross-Functional Collaboration:</strong> Proven ability to work closely with
    <strong>product managers</strong>, <strong>engineers</strong>, and
    <strong>business stakeholders</strong> to drive design maturity and ship
    user-focused products at scale.
  </li>
  <li>
    <strong>Design Leadership:</strong> Led product and design initiatives at
    <strong>Squareboat</strong>, owning the full design lifecycle from discovery and
    wireframing through to final delivery and QA handoff.
  </li>
</ul>

<p>
I am particularly drawn to organizations that value <strong>strong product thinking</strong>,
<strong>design maturity</strong>, and a culture where design has a meaningful seat at the table.
</p>

<p>
I have attached my resume for your reference. My portfolio (selected work) is available here:<br>
<a href="https://basalt-newsboy-98f.notion.site/Aakriti-Jain-2fe3fa8a7371803f8dbee298d32ec70c"
   style="color: #0066cc;">
  🔗 Portfolio — Aakriti Jain
</a>
</p>

<p>
I have also contributed to several additional products and case studies not yet publicly live —
I would be happy to walk through them during a conversation if relevant.
</p>

<p>
I would truly appreciate the opportunity to connect and explore any suitable openings within
your team. Thank you for your time, and I look forward to hearing from you.
</p>

<p>
Warm regards,<br>
<strong>Aakriti Jain</strong><br>
Product Designer | UI/UX Lead<br>
8766347359<br>
<a href="https://www.linkedin.com/in/aakriti-jain-designer/"
   style="color: #0066cc;">LinkedIn Profile</a>
&nbsp;·&nbsp;
<a href="https://basalt-newsboy-98f.notion.site/Aakriti-Jain-2fe3fa8a7371803f8dbee298d32ec70c"
   style="color: #0066cc;">Portfolio</a>
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