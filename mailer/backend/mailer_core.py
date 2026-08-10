"""
Core email-sender logic (from No_Limit.py), usable by the API.
Credentials come from environment / request config — never hardcode passwords.
"""

from __future__ import annotations

import csv
import imaplib
import logging
import mimetypes
import os
import random
import re
import smtplib
import time
import email as email_lib
from datetime import date
from email.message import EmailMessage
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,7}")

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

DEFAULT_SUBJECT = (
    "QA Automation Engineer / SDET "
    "— 4 Years of Experience in Test Automation & CI/CD Integration"
)

DEFAULT_BODY = """\
<p>Dear Hiring Manager,</p>
<p>
I am writing to express my strong interest in a QA Automation Engineer / SDET opportunity
at your organization. With <strong>4 years</strong> of hands-on experience building and scaling
test automation frameworks, I am confident in my ability to deliver measurable improvements
in software quality, release velocity, and test coverage.
</p>
<p><strong>Here is a brief overview of what I bring to the role:</strong></p>
<ul>
  <li><strong>Automation Frameworks:</strong> Playwright, Selenium, and Appium.</li>
  <li><strong>API &amp; Integration Testing:</strong> Postman-based REST API validation.</li>
  <li><strong>Test Strategy:</strong> Regression suites and release-ready test plans.</li>
  <li><strong>CI/CD Integration:</strong> Automated pipelines using Pytest.</li>
</ul>
<p>I have attached my resume and would welcome a brief call to discuss fit.</p>
<p>Thank you for your time.</p>
<p>Warm regards,<br><strong>Chirag Khanduja</strong><br>QA Automation Engineer | SDET<br>903-422-6868</p>
"""


def setup_logger(log_file: Path) -> logging.Logger:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("mailer_api")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_file)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


def is_valid_email(email: str) -> bool:
    try:
        local, domain = email.rsplit("@", 1)
    except ValueError:
        return False
    if local.startswith(("-", ".", "_", "+")) or local.endswith(("-", ".", "_", "+")):
        return False
    if ".." in email or len(local) < 1:
        return False
    if "." not in domain or domain.startswith("-") or domain.endswith("-"):
        return False
    return True


def load_sent_emails(sent_file: Path) -> Set[str]:
    if not sent_file.exists():
        return set()
    with sent_file.open(newline="") as f:
        return {row[0].strip().lower() for row in csv.reader(f) if row}


def mark_sent(sent_file: Path, email: str) -> None:
    sent_file.parent.mkdir(parents=True, exist_ok=True)
    with sent_file.open("a", newline="") as f:
        csv.writer(f).writerow([email])


def update_daily_log(log_file: Path, count: int) -> None:
    today = date.today().isoformat()
    rows: List[List[str]] = [["Date", "Count"]]
    if log_file.exists():
        with log_file.open(newline="") as f:
            rows = list(csv.reader(f))
    updated = False
    for row in rows[1:]:
        if row and row[0] == today:
            row[1] = str(int(row[1]) + count)
            updated = True
            break
    if not updated:
        rows.append([today, str(count)])
    with log_file.open("w", newline="") as f:
        csv.writer(f).writerows(rows)


def extract_emails_from_pdfs(
    pdf_paths: List[str],
    excluded_domains: Set[str],
    excluded_emails: Set[str],
    log: Optional[Callable[[str], None]] = None,
) -> Dict[str, int]:
    import pdfplumber

    # Harmless pdfminer noise on many job-list PDFs (CropBox → MediaBox).
    logging.getLogger("pdfminer").setLevel(logging.ERROR)

    counts: Dict[str, int] = {}
    skipped = 0
    for path_str in pdf_paths:
        path = Path(path_str)
        if not path.exists():
            if log:
                log(f"Missing PDF: {path}")
            continue
        if log:
            log(f"Reading PDF: {path.name}")
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for match in EMAIL_RE.findall(text):
                    email = match.lower().strip()
                    if not is_valid_email(email):
                        skipped += 1
                        continue
                    domain = email.split("@")[-1]
                    if domain in excluded_domains or email in excluded_emails:
                        continue
                    counts[email] = counts.get(email, 0) + 1
    if log:
        log(f"Unique valid emails: {len(counts)} | skipped invalid: {skipped}")
    return counts


def parse_emails_from_text(
    text: str,
    excluded_domains: Optional[Set[str]] = None,
    excluded_emails: Optional[Set[str]] = None,
) -> List[str]:
    """Parse emails from paste text (one per line, comma/semicolon separated, or free text)."""
    excluded_domains = excluded_domains or set()
    excluded_emails = excluded_emails or set()
    found: List[str] = []
    seen: Set[str] = set()
    for match in EMAIL_RE.findall(text or ""):
        email = match.lower().strip()
        if not is_valid_email(email) or email in seen:
            continue
        domain = email.split("@")[-1]
        if domain in excluded_domains or email in excluded_emails:
            continue
        seen.add(email)
        found.append(email)
    return found


def load_emails_from_csv(
    csv_path: str,
    excluded_domains: Optional[Set[str]] = None,
    excluded_emails: Optional[Set[str]] = None,
    log: Optional[Callable[[str], None]] = None,
) -> List[str]:
    """Load emails from CSV (Email column or first column)."""
    excluded_domains = excluded_domains or set()
    excluded_emails = excluded_emails or set()
    path = Path(csv_path)
    if not path.exists():
        if log:
            log(f"CSV not found: {path}")
        return []

    emails: List[str] = []
    seen: Set[str] = set()
    with path.open(newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        has_header = "email" in sample.lower().split("\n", 1)[0]
        if has_header:
            reader = csv.DictReader(f)
            col = next(
                (c for c in (reader.fieldnames or []) if c and c.strip().lower() == "email"),
                None,
            )
            if col:
                for row in reader:
                    raw = (row.get(col) or "").strip().lower()
                    if raw and EMAIL_RE.fullmatch(raw) and is_valid_email(raw):
                        emails.append(raw)
            else:
                f.seek(0)
                plain = csv.reader(f)
                next(plain, None)
                for row in plain:
                    if row:
                        emails.append(row[0].strip().lower())
        else:
            for row in csv.reader(f):
                if row:
                    emails.append(row[0].strip().lower())

    unique: List[str] = []
    for e in emails:
        if not EMAIL_RE.fullmatch(e) or not is_valid_email(e) or e in seen:
            continue
        domain = e.split("@")[-1]
        if domain in excluded_domains or e in excluded_emails:
            continue
        seen.add(e)
        unique.append(e)
    if log:
        log(f"Loaded {len(unique)} email(s) from CSV: {path.name}")
    return unique


def get_today_sent_count(log_file: Path) -> int:
    today = date.today().isoformat()
    if not log_file.exists():
        return 0
    with log_file.open(newline="") as f:
        rows = list(csv.reader(f))
    for row in rows[1:]:
        if row and row[0] == today:
            try:
                return int(row[1])
            except ValueError:
                return 0
    return 0


class HourlyRateLimiter:
    def __init__(self, max_per_hour: int, log: Optional[Callable[[str], None]] = None):
        self.max_per_hour = max_per_hour
        self.timestamps: List[float] = []
        self.log = log or (lambda _: None)

    def wait_if_needed(self, stop_flag: Optional[Callable[[], bool]] = None) -> bool:
        """Return False if stopped while waiting."""
        if self.max_per_hour <= 0:
            return True
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t < 3600]
        if len(self.timestamps) < self.max_per_hour:
            return True
        oldest = self.timestamps[0]
        wait_secs = 3600 - (now - oldest) + 5
        self.log(f"Hourly limit reached. Waiting {wait_secs / 60:.0f} minutes…")
        elapsed = 0.0
        while elapsed < wait_secs:
            if stop_flag and stop_flag():
                return False
            chunk = min(30, wait_secs - elapsed)
            time.sleep(chunk)
            elapsed += chunk
        self.timestamps = []
        return True

    def record(self) -> None:
        self.timestamps.append(time.time())


def fetch_bounced_emails(account: dict, log: Optional[Callable[[str], None]] = None) -> Set[str]:
    bounced: Set[str] = set()
    try:
        if log:
            log(f"Checking bounces via IMAP ({account['email']})…")
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(account["email"], account["password"])
        mail.select("inbox")
        for sender in BOUNCE_SENDERS:
            _, data = mail.search(None, f'FROM "{sender}"')
            ids = data[0].split()
            for num in ids:
                _, msg_data = mail.fetch(num, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)
                subject = (msg.get("Subject") or "").lower()
                if not any(kw in subject for kw in BOUNCE_SUBJECTS):
                    continue
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() in ("text/plain", "text/html"):
                            try:
                                body += part.get_payload(decode=True).decode(errors="ignore")
                            except Exception:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    except Exception:
                        pass
                for addr in EMAIL_RE.findall(body):
                    addr = addr.lower().strip()
                    if any(d in addr for d in ["mailer-daemon", "googlemail", "gmail.com", "google.com"]):
                        continue
                    bounced.add(addr)
        mail.logout()
        if log:
            log(f"Bounce check done — {len(bounced)} address(es).")
    except Exception as exc:
        if log:
            log(f"IMAP bounce check failed (non-critical): {exc}")
    return bounced


def mark_bounced(sent_file: Path, emails: Set[str], log: Optional[Callable[[str], None]] = None) -> None:
    if not emails:
        return
    existing = load_sent_emails(sent_file)
    new_bounced = emails - existing
    if not new_bounced:
        return
    sent_file.parent.mkdir(parents=True, exist_ok=True)
    with sent_file.open("a", newline="") as f:
        writer = csv.writer(f)
        for addr in new_bounced:
            writer.writerow([addr])
    if log:
        log(f"Marked {len(new_bounced)} bounced email(s) as do-not-send.")


def build_message(
    to_email: str,
    from_email: str,
    reply_to: str,
    subject: str,
    body_html: str,
    attachment_data: bytes,
    attach_mime: str,
    attach_name: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Reply-To"] = reply_to
    msg["Subject"] = subject
    msg.add_alternative(body_html, subtype="html")
    maintype, subtype = attach_mime.split("/", 1)
    msg.add_attachment(
        attachment_data, maintype=maintype, subtype=subtype, filename=attach_name
    )
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


def connect_smtp(
    account: dict,
    timeout: int = 30,
    max_retries: int = 3,
    retry_wait: Tuple[float, float] = (10, 20),
    log: Optional[Callable[[str], None]] = None,
) -> Union[smtplib.SMTP, smtplib.SMTP_SSL]:
    email, password = account["email"], account["password"]
    for attempt in range(1, max_retries + 1):
        try:
            server = _try_starttls(email, password, timeout)
            if log:
                log(f"Connected via 587 as {email} (attempt {attempt})")
            return server
        except (TimeoutError, OSError, smtplib.SMTPException) as exc:
            if log:
                log(f"Port 587 failed ({email}, {attempt}/{max_retries}): {exc}")
        try:
            server = _try_ssl(email, password, timeout)
            if log:
                log(f"Connected via 465 as {email} (attempt {attempt})")
            return server
        except (TimeoutError, OSError, smtplib.SMTPException) as exc:
            if log:
                log(f"Port 465 failed ({email}, {attempt}/{max_retries}): {exc}")
        if attempt < max_retries:
            wait = random.uniform(*retry_wait)
            if log:
                log(f"Retrying in {wait:.0f}s…")
            time.sleep(wait)
    raise RuntimeError(f"Could not connect with account: {email}")


def connect_smtp_with_fallback(
    accounts: List[dict],
    current_index: int,
    log: Optional[Callable[[str], None]] = None,
) -> Tuple[Union[smtplib.SMTP, smtplib.SMTP_SSL], int]:
    for idx in range(current_index, len(accounts)):
        try:
            return connect_smtp(accounts[idx], log=log), idx
        except RuntimeError:
            if log:
                log(f"Account {accounts[idx]['email']} exhausted, trying next…")
    raise RuntimeError("All Gmail accounts exhausted.")


def parse_accounts_from_env() -> List[dict]:
    """
    GMAIL_ACCOUNTS format:
      email1:app_password1;email2:app_password2
    Or single:
      GMAIL_ADDRESS + GMAIL_APP_PASSWORD
    """
    raw = os.environ.get("GMAIL_ACCOUNTS", "").strip()
    accounts: List[dict] = []
    if raw:
        for part in raw.split(";"):
            part = part.strip()
            if not part or ":" not in part:
                continue
            email, password = part.split(":", 1)
            accounts.append({"email": email.strip(), "password": password.strip()})
    else:
        email = os.environ.get("GMAIL_ADDRESS", "").strip()
        password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
        if email and password:
            accounts.append({"email": email, "password": password})
    return accounts


class SendConfig:
    def __init__(
        self,
        accounts: List[dict],
        reply_to: str,
        subject: str,
        body_html: str,
        attachment_path: str,
        data_dir: Path,
        pdf_paths: Optional[List[str]] = None,
        manual_emails: Optional[List[str]] = None,
        mode: str = "pdf",  # "pdf" | "manual"
        dry_run: bool = False,
        check_bounces: bool = True,
        warmup_mode: bool = False,
        batch_size: int = 50,
        per_email_delay: Tuple[float, float] = (3, 7),
        warmup_delay: Tuple[float, float] = (8, 15),
        domain_burst_size: int = 2,
        domain_burst_pause: Tuple[float, float] = (15, 30),
        session_break: Tuple[float, float] = (600, 1200),
        excluded_domains: Optional[Set[str]] = None,
        excluded_emails: Optional[Set[str]] = None,
        daily_cap: Optional[int] = None,
        max_per_hour: Optional[int] = None,
        skip_already_sent: bool = True,
        respect_daily_log_cap: bool = False,
        stop_flag: Optional[Callable[[], bool]] = None,
        on_progress: Optional[Callable[[dict], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ):
        self.accounts = accounts
        self.reply_to = reply_to
        self.subject = subject
        self.body_html = body_html
        self.pdf_paths = pdf_paths or []
        self.manual_emails = manual_emails
        self.mode = mode
        self.attachment_path = attachment_path
        self.data_dir = data_dir
        self.dry_run = dry_run
        self.check_bounces = check_bounces
        self.warmup_mode = warmup_mode
        self.batch_size = batch_size
        self.per_email_delay = per_email_delay
        self.warmup_delay = warmup_delay
        self.domain_burst_size = domain_burst_size
        self.domain_burst_pause = domain_burst_pause
        self.session_break = session_break
        self.excluded_domains = excluded_domains or set()
        self.excluded_emails = excluded_emails or set()
        self.daily_cap = daily_cap
        self.max_per_hour = max_per_hour
        self.skip_already_sent = skip_already_sent
        self.respect_daily_log_cap = respect_daily_log_cap
        self.stop_flag = stop_flag or (lambda: False)
        self.on_progress = on_progress or (lambda _: None)
        self.on_log = on_log or (lambda _: None)

    @property
    def sent_file(self) -> Path:
        return self.data_dir / "sent_emails.csv"

    @property
    def daily_log_file(self) -> Path:
        return self.data_dir / "email_log.csv"

    @property
    def preview_file(self) -> Path:
        return self.data_dir / "preview_recipients.csv"


def run_send_job(cfg: SendConfig) -> dict:
    log = cfg.on_log
    attach_path = Path(cfg.attachment_path)
    if not attach_path.exists():
        raise FileNotFoundError(f"Resume not found: {attach_path}")
    if not cfg.accounts:
        raise RuntimeError("No Gmail accounts configured. Set GMAIL_ACCOUNTS or GMAIL_ADDRESS/GMAIL_APP_PASSWORD.")

    if cfg.check_bounces:
        for acc in cfg.accounts:
            bounced = fetch_bounced_emails(acc, log=log)
            mark_bounced(cfg.sent_file, bounced, log=log)

    effective_delay = cfg.warmup_delay if cfg.warmup_mode else cfg.per_email_delay
    if cfg.warmup_mode:
        log("WARM-UP MODE active — slower delays")

    occurrence: Dict[str, int] = {}
    if cfg.manual_emails is not None:
        log(f"Manual mode — {len(cfg.manual_emails)} recipient(s) provided")
        for e in cfg.manual_emails:
            occurrence[e] = occurrence.get(e, 0) + 1
        all_emails = occurrence
        ordered = list(dict.fromkeys(cfg.manual_emails))
    else:
        all_emails = extract_emails_from_pdfs(
            cfg.pdf_paths, cfg.excluded_domains, cfg.excluded_emails, log=log
        )
        ordered = sorted(all_emails.keys())

    sent_before = load_sent_emails(cfg.sent_file)
    if cfg.skip_already_sent:
        send_list = [e for e in ordered if e not in sent_before]
    else:
        send_list = list(ordered)

    # EmailManual-style: remaining room under today's daily log count
    effective_cap = cfg.daily_cap
    if cfg.respect_daily_log_cap and cfg.daily_cap is not None:
        already_today = get_today_sent_count(cfg.daily_log_file)
        remaining = max(0, cfg.daily_cap - already_today)
        log(
            f"Daily cap: {cfg.daily_cap} | sent today: {already_today} | remaining: {remaining}"
        )
        effective_cap = remaining
    if effective_cap is not None:
        send_list = send_list[: effective_cap]

    result = {
        "total_found": len(all_emails),
        "already_sent": len(sent_before),
        "queued": len(send_list),
        "sent": 0,
        "dry_run": cfg.dry_run,
        "stopped": False,
        "mode": cfg.mode,
    }
    cfg.on_progress({**result, "running": True, "phase": "queued"})

    if not send_list:
        log("No new recipients — nothing to do.")
        cfg.on_progress({**result, "running": False, "phase": "done"})
        return result

    if cfg.dry_run:
        log(f"DRY RUN — writing preview to {cfg.preview_file}")
        with cfg.preview_file.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Email", "Occurrences"])
            for e in send_list:
                writer.writerow([e, all_emails.get(e, 1)])
        log(f"Preview written ({len(send_list)} rows).")
        cfg.on_progress({**result, "running": False, "phase": "preview"})
        return result

    attach_data = attach_path.read_bytes()
    attach_mime = mimetypes.guess_type(str(attach_path))[0] or "application/octet-stream"
    attach_name = attach_path.name

    total = len(send_list)
    sent_count = 0
    domain_count: Dict[str, int] = {}
    rate_limiter = HourlyRateLimiter(cfg.max_per_hour or 0, log=log)
    account_idx = 0
    server, account_idx = connect_smtp_with_fallback(cfg.accounts, account_idx, log=log)
    current_email = cfg.accounts[account_idx]["email"]
    log(
        f"Starting send ({cfg.mode}): {total} emails | Batch: {cfg.batch_size}"
        + (f" | Max/hour: {cfg.max_per_hour}" if cfg.max_per_hour else "")
        + f" | Account: {current_email}"
    )

    for i, to_email in enumerate(send_list):
        if cfg.stop_flag():
            log("Stop requested — ending send job.")
            result["stopped"] = True
            break

        if not rate_limiter.wait_if_needed(cfg.stop_flag):
            log("Stop requested during hourly wait.")
            result["stopped"] = True
            break

        if i > 0 and i % cfg.batch_size == 0:
            pause = random.uniform(*cfg.session_break)
            log(
                f"Batch {i // cfg.batch_size} complete ({sent_count} sent). "
                f"Session break: {pause / 60:.0f} minutes…"
            )
            try:
                server.quit()
            except Exception:
                pass
            elapsed = 0.0
            while elapsed < pause:
                if cfg.stop_flag():
                    log("Stop requested during session break.")
                    result["stopped"] = True
                    break
                sleep_chunk = min(30, pause - elapsed)
                time.sleep(sleep_chunk)
                elapsed += sleep_chunk
            if result["stopped"]:
                break
            server, account_idx = connect_smtp_with_fallback(cfg.accounts, account_idx, log=log)
            current_email = cfg.accounts[account_idx]["email"]

        msg = build_message(
            to_email,
            current_email,
            cfg.reply_to,
            cfg.subject,
            cfg.body_html,
            attach_data,
            attach_mime,
            attach_name,
        )
        try:
            server.send_message(msg)
            sent_count += 1
            rate_limiter.record()
            mark_sent(cfg.sent_file, to_email)
            log(f"Sent [{sent_count}/{total}] → {to_email} (via {current_email})")
        except smtplib.SMTPRecipientsRefused:
            log(f"Refused: {to_email}")
        except smtplib.SMTPServerDisconnected:
            log("Disconnected — reconnecting…")
            try:
                server, account_idx = connect_smtp_with_fallback(cfg.accounts, account_idx, log=log)
                current_email = cfg.accounts[account_idx]["email"]
                msg = build_message(
                    to_email, current_email, cfg.reply_to, cfg.subject, cfg.body_html,
                    attach_data, attach_mime, attach_name,
                )
                server.send_message(msg)
                sent_count += 1
                rate_limiter.record()
                mark_sent(cfg.sent_file, to_email)
                log(f"Sent (retry) [{sent_count}/{total}] → {to_email}")
            except Exception as exc:
                log(f"Retry failed for {to_email}: {exc}")
        except smtplib.SMTPException as exc:
            err_str = str(exc).lower()
            if any(k in err_str for k in ("daily limit", "quota", "too many", "temporarily", "suspended", "rate")):
                log(f"Account {current_email} hit a limit — switching…")
                try:
                    server.quit()
                except Exception:
                    pass
                account_idx += 1
                try:
                    server, account_idx = connect_smtp_with_fallback(cfg.accounts, account_idx, log=log)
                    current_email = cfg.accounts[account_idx]["email"]
                    msg = build_message(
                        to_email, current_email, cfg.reply_to, cfg.subject, cfg.body_html,
                        attach_data, attach_mime, attach_name,
                    )
                    server.send_message(msg)
                    sent_count += 1
                    rate_limiter.record()
                    mark_sent(cfg.sent_file, to_email)
                    log(f"Sent (switched) [{sent_count}/{total}] → {to_email}")
                except RuntimeError:
                    log("All accounts exhausted. Stopping.")
                    break
                except Exception as exc2:
                    log(f"Failed after switch for {to_email}: {exc2}")
            else:
                log(f"SMTP error for {to_email}: {exc}")
        except Exception as exc:
            log(f"Unexpected error for {to_email}: {exc}")

        result["sent"] = sent_count
        cfg.on_progress({**result, "running": True, "phase": "sending", "current": to_email})

        domain = to_email.split("@")[-1]
        domain_count[domain] = domain_count.get(domain, 0) + 1
        if domain_count[domain] % cfg.domain_burst_size == 0:
            time.sleep(random.uniform(*cfg.domain_burst_pause))
        time.sleep(random.uniform(*effective_delay))

    try:
        server.quit()
    except Exception:
        pass

    if sent_count:
        update_daily_log(cfg.daily_log_file, sent_count)
    result["sent"] = sent_count
    log(f"Done — {sent_count}/{total} emails sent.")
    cfg.on_progress({**result, "running": False, "phase": "done"})
    return result
