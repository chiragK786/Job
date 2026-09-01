#!/usr/bin/env python3
"""
MAILER + TRACKING — combined dashboard
Runs the tracking pixel endpoint and a web UI in ONE process, so you don't
need to run two scripts separately.

  pip install flask pdfplumber
  export GMAIL_ADDRESS="you@gmail.com"
  export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
  python app.py

Then open http://localhost:5000 in your browser.

If you want opens to be tracked when recipients are on a different network
than your machine, deploy this (e.g. small VPS / Render / PythonAnywhere)
or expose it temporarily with ngrok, and make sure PUBLIC_BASE_URL below
matches the address recipients' email clients can actually reach.
"""

import re
import csv
import os
import time
import random
import uuid
import mimetypes
import smtplib
import threading
import logging
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, Set, List

from flask import Flask, Response, request, jsonify, render_template_string

# ─────────────────────────────────────────────
#  CONFIG — edit these
# ─────────────────────────────────────────────
PDF_PATHS: List[str] = [
    "WFH Remote Outside India (5).pdf",
]
ATTACHMENT_PATH = "Chirag_Khanduja_SDET_QA_AI_Tester.pdf"

GMAIL_ADDRESS      = os.environ.get("GMAIL_ADDRESS", "chiragkhanduja786@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "ivci swwm gwfx btku")
REPLY_TO = GMAIL_ADDRESS

# Public URL where THIS app is reachable (used inside the tracking pixel).
# If testing locally with no real recipients, leave as localhost.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "http://localhost:5000")

EXCLUDED_DOMAINS: Set[str] = set()
EXCLUDED_EMAILS: Set[str]  = set()

PER_EMAIL_DELAY = (5, 12)
DAILY_SEND_CAP  = 400

EMAIL_SUBJECT = (
    "QA Automation Engineer / SDET "
    "— 4 Years of Experience in Test Automation & CI/CD Integration"
)

EMAIL_BODY_TEMPLATE = """\
<html><body>
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
<p style="font-size:11px;color:#888;">
If you'd prefer not to receive emails like this, just reply "unsubscribe".
</p>
{tracking_pixel}
</body></html>
"""

BASE_DIR         = Path(__file__).parent
SENT_EMAILS_FILE = BASE_DIR / "sent_emails.csv"
OPENS_FILE       = BASE_DIR / "opens.csv"
APP_LOG_FILE     = BASE_DIR / "app.log"

PIXEL_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c6360000002000100ffff03000006000557bfabd4000000"
    "0049454e44ae426082"
)

# ─────────────────────────────────────────────
#  LOGGING (in-memory ring buffer so the UI can show live logs)
# ─────────────────────────────────────────────
log_lines: List[str] = []
log_lock = threading.Lock()

def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')}  {msg}"
    print(line)
    with log_lock:
        log_lines.append(line)
        del log_lines[:-300]   # keep last 300 lines
    with APP_LOG_FILE.open("a") as f:
        f.write(line + "\n")

# ─────────────────────────────────────────────
#  SENT TRACKING
# ─────────────────────────────────────────────
def load_sent_emails() -> Set[str]:
    if not SENT_EMAILS_FILE.exists():
        return set()
    with SENT_EMAILS_FILE.open(newline="") as f:
        return {row[0].strip().lower() for row in csv.reader(f) if row}

def mark_sent(email: str) -> None:
    with SENT_EMAILS_FILE.open("a", newline="") as f:
        csv.writer(f).writerow([email])

# ─────────────────────────────────────────────
#  EMAIL EXTRACTION
# ─────────────────────────────────────────────
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,7}")

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

def extract_emails_from_pdfs(pdf_paths: List[str]) -> Dict[str, int]:
    import pdfplumber
    counts: Dict[str, int] = {}
    for path_str in pdf_paths:
        path = Path(path_str)
        if not path.exists():
            log(f"⚠ Missing PDF: {path}")
            continue
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for match in EMAIL_RE.findall(text):
                    email = match.lower().strip()
                    if not is_valid_email(email):
                        continue
                    domain = email.split("@")[-1]
                    if domain in EXCLUDED_DOMAINS or email in EXCLUDED_EMAILS:
                        continue
                    counts[email] = counts.get(email, 0) + 1
    return counts

# ─────────────────────────────────────────────
#  MESSAGE + SMTP
# ─────────────────────────────────────────────
def build_message(to_email: str, attach_data: bytes, attach_mime: str, attach_name: str) -> EmailMessage:
    tracking_id = uuid.uuid4().hex
    tracking_url = f"{PUBLIC_BASE_URL}/track/{tracking_id}"
    tracking_pixel = f'<img src="{tracking_url}" width="1" height="1" style="display:none;">'
    body = EMAIL_BODY_TEMPLATE.format(tracking_pixel=tracking_pixel)

    msg = EmailMessage()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email
    msg["Reply-To"] = REPLY_TO
    msg["Subject"] = EMAIL_SUBJECT
    msg.add_alternative(body, subtype="html")
    maintype, subtype = attach_mime.split("/", 1)
    msg.add_attachment(attach_data, maintype=maintype, subtype=subtype, filename=attach_name)
    return msg

def connect_smtp() -> smtplib.SMTP:
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise RuntimeError("Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD env vars first.")
    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
    return server

# ─────────────────────────────────────────────
#  SENDING JOB (runs in a background thread)
# ─────────────────────────────────────────────
job_state = {
    "running": False,
    "total": 0,
    "sent": 0,
    "started_at": None,
    "finished_at": None,
}
job_lock = threading.Lock()

def run_send_job():
    with job_lock:
        if job_state["running"]:
            log("⚠ Send job already running, ignoring duplicate start.")
            return
        job_state.update(running=True, total=0, sent=0,
                          started_at=time.strftime("%Y-%m-%d %H:%M:%S"), finished_at=None)

    try:
        attach_path = Path(ATTACHMENT_PATH)
        if not attach_path.exists():
            log(f"✘ Attachment not found: {attach_path}")
            return

        all_emails = extract_emails_from_pdfs(PDF_PATHS)
        sent_before = load_sent_emails()
        send_list = sorted(e for e in all_emails if e not in sent_before)[:DAILY_SEND_CAP]

        job_state["total"] = len(send_list)
        log(f"Starting send job: {len(send_list)} new recipients (cap {DAILY_SEND_CAP})")

        if not send_list:
            log("Nothing new to send.")
            return

        attach_data = attach_path.read_bytes()
        attach_mime = mimetypes.guess_type(str(attach_path))[0] or "application/octet-stream"
        attach_name = attach_path.name

        server = connect_smtp()
        for to_email in send_list:
            try:
                msg = build_message(to_email, attach_data, attach_mime, attach_name)
                server.send_message(msg)
                mark_sent(to_email)
                job_state["sent"] += 1
                log(f"✔ Sent [{job_state['sent']}/{job_state['total']}] -> {to_email}")
            except smtplib.SMTPRecipientsRefused:
                log(f"✘ Refused: {to_email}")
            except smtplib.SMTPServerDisconnected:
                log("Disconnected, reconnecting…")
                server = connect_smtp()
            except Exception as exc:
                log(f"✘ Error sending to {to_email}: {exc}")

            time.sleep(random.uniform(*PER_EMAIL_DELAY))

        try:
            server.quit()
        except Exception:
            pass
        log(f"🎉 Done — {job_state['sent']}/{job_state['total']} sent.")
    finally:
        with job_lock:
            job_state["running"] = False
            job_state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

# ─────────────────────────────────────────────
#  FLASK APP
# ─────────────────────────────────────────────
app = Flask(__name__)

@app.route("/track/<tracking_id>")
def track(tracking_id):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    is_new = not OPENS_FILE.exists()
    with OPENS_FILE.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["tracking_id", "timestamp", "ip"])
        writer.writerow([tracking_id, timestamp, ip])
    log(f"👁 Opened: {tracking_id} from {ip}")
    return Response(PIXEL_BYTES, mimetype="image/png")

@app.route("/api/preview")
def api_preview():
    all_emails = extract_emails_from_pdfs(PDF_PATHS)
    sent_before = load_sent_emails()
    new_count = len([e for e in all_emails if e not in sent_before])
    return jsonify(total_found=len(all_emails), already_sent=len(sent_before), new_to_send=new_count)

@app.route("/api/start", methods=["POST"])
def api_start():
    if job_state["running"]:
        return jsonify(ok=False, error="A send job is already running."), 409
    threading.Thread(target=run_send_job, daemon=True).start()
    return jsonify(ok=True)

@app.route("/api/status")
def api_status():
    with log_lock:
        tail = log_lines[-100:]
    opens = 0
    if OPENS_FILE.exists():
        with OPENS_FILE.open(newline="") as f:
            opens = max(0, sum(1 for _ in f) - 1)
    return jsonify(job=job_state, log=tail, opens=opens)

DASHBOARD_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Mailer Dashboard</title>
<style>
  :root {
    --bg: #0b0e0f;
    --panel: #12171a;
    --border: #223;
    --text: #d7ded9;
    --dim: #7c8a86;
    --accent: #5ec9a4;
    --accent-dim: #2f5b4c;
    --warn: #e0a63c;
  }
  * { box-sizing: border-box; }
  body {
    background: var(--bg); color: var(--text);
    font-family: 'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace;
    margin: 0; padding: 32px; font-size: 14px;
  }
  h1 { font-size: 18px; letter-spacing: 0.5px; margin: 0 0 4px; color: var(--accent); }
  .sub { color: var(--dim); margin-bottom: 28px; font-size: 12.5px; }
  .grid { display: grid; grid-template-columns: 260px 1fr; gap: 20px; align-items: start; }
  .panel {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 6px; padding: 18px;
  }
  .stat { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed var(--border); font-size: 13px; }
  .stat:last-child { border-bottom: none; }
  .stat b { color: var(--accent); font-weight: 600; }
  button {
    width: 100%; padding: 10px; margin-top: 10px;
    background: transparent; border: 1px solid var(--accent-dim);
    color: var(--accent); font-family: inherit; font-size: 13px;
    border-radius: 4px; cursor: pointer; transition: all .15s;
  }
  button:hover { background: var(--accent-dim); }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  #log {
    background: #05070800; height: 480px; overflow-y: auto;
    font-size: 12.5px; line-height: 1.6; white-space: pre-wrap;
  }
  .badge { display:inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; margin-left: 8px; }
  .badge.on { background: var(--accent-dim); color: var(--accent); }
  .badge.off { background: #333; color: var(--dim); }
  .warn { color: var(--warn); font-size: 12px; margin-top: 10px; }
</style>
</head>
<body>
  <h1>&gt; MAILER<span id="status-badge" class="badge off">idle</span></h1>
  <div class="sub">single account · rate-limited · tracked opens</div>

  <div class="grid">
    <div class="panel">
      <div class="stat"><span>Emails found</span><b id="s-found">–</b></div>
      <div class="stat"><span>Already sent</span><b id="s-sent-before">–</b></div>
      <div class="stat"><span>New to send</span><b id="s-new">–</b></div>
      <div class="stat"><span>Sent this run</span><b id="s-sent-now">0 / 0</b></div>
      <div class="stat"><span>Opens tracked</span><b id="s-opens">0</b></div>
      <button id="btn-preview" onclick="preview()">Refresh preview</button>
      <button id="btn-start" onclick="startSend()">Start sending</button>
      <div class="warn">Sends from one Gmail account, ~5–12s apart, capped per run. No rotation, no evasion.</div>
    </div>
    <div class="panel">
      <div id="log"></div>
    </div>
  </div>

<script>
async function preview() {
  const r = await fetch('/api/preview');
  const d = await r.json();
  document.getElementById('s-found').textContent = d.total_found;
  document.getElementById('s-sent-before').textContent = d.already_sent;
  document.getElementById('s-new').textContent = d.new_to_send;
}
async function startSend() {
  document.getElementById('btn-start').disabled = true;
  const r = await fetch('/api/start', {method: 'POST'});
  if (!r.ok) { const d = await r.json(); alert(d.error || 'Could not start'); }
}
async function poll() {
  const r = await fetch('/api/status');
  const d = await r.json();
  const badge = document.getElementById('status-badge');
  badge.textContent = d.job.running ? 'sending' : 'idle';
  badge.className = 'badge ' + (d.job.running ? 'on' : 'off');
  document.getElementById('s-sent-now').textContent = d.job.sent + ' / ' + d.job.total;
  document.getElementById('s-opens').textContent = d.opens;
  document.getElementById('btn-start').disabled = d.job.running;
  const logEl = document.getElementById('log');
  const atBottom = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 10;
  logEl.textContent = d.log.join('\\n');
  if (atBottom) logEl.scrollTop = logEl.scrollHeight;
}
preview();
poll();
setInterval(poll, 2000);
</script>
</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)