#!/usr/bin/env python3
"""
Mailer API — FastAPI wrapper around No_Limit send logic.

  cd mailer/backend
  pip install -r requirements.txt
  export GMAIL_ADDRESS="you@gmail.com"
  export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
  export API_KEY="pick-a-long-random-secret"
  uvicorn main:app --host 0.0.0.0 --port 8000

Free backend hosts (no card): PythonAnywhere free, Fly.io trial sometimes,
or run on your laptop + Cloudflare Tunnel / ngrok free.
"""

from __future__ import annotations

import os
import secrets
import shutil
import threading
import time
from pathlib import Path
from typing import List, Optional, Set

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from mailer_core import (
    DEFAULT_BODY,
    DEFAULT_SUBJECT,
    SendConfig,
    extract_emails_from_pdfs,
    get_today_sent_count,
    load_emails_from_csv,
    load_sent_emails,
    parse_accounts_from_env,
    parse_emails_from_text,
    run_send_job,
)

BASE_DIR = Path(__file__).resolve().parent
# frontend/ sits next to backend/ in the mailer/ folder (also copied into image)
FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", BASE_DIR.parent / "frontend"))
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = BASE_DIR / "frontend"

DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

API_KEY = os.environ.get("API_KEY", "").strip()
# Allow all origins by default so a free static host can call this API.
# Lock down with CORS_ORIGINS="https://your-site.pages.dev" in production.
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "*").split(",")
    if o.strip()
]

app = FastAPI(title="Mailer API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

log_lines: List[str] = []
log_lock = threading.Lock()
job_lock = threading.Lock()
stop_requested = False

job_state = {
    "running": False,
    "phase": "idle",
    "mode": None,
    "total_found": 0,
    "already_sent": 0,
    "queued": 0,
    "sent": 0,
    "dry_run": False,
    "stopped": False,
    "current": None,
    "started_at": None,
    "finished_at": None,
    "error": None,
}


def push_log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')}  {msg}"
    print(line, flush=True)
    with log_lock:
        log_lines.append(line)
        del log_lines[:-400]


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    if not API_KEY:
        # Dev mode: no key configured → open (local only). Set API_KEY in prod.
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


class PreviewResponse(BaseModel):
    total_found: int
    already_sent: int
    new_to_send: int
    sample: List[str] = Field(default_factory=list)
    sent_today: int = 0
    remaining_today: Optional[int] = None
    mode: str = "pdf"


class StatusResponse(BaseModel):
    job: dict
    log: List[str]
    accounts_configured: int
    has_api_key: bool


class HealthResponse(BaseModel):
    ok: bool
    service: str = "mailer-api"


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(ok=True)


@app.get("/api/status", response_model=StatusResponse, dependencies=[Depends(require_api_key)])
def status():
    with log_lock:
        tail = list(log_lines[-120:])
    return StatusResponse(
        job=job_state,
        log=tail,
        accounts_configured=len(parse_accounts_from_env()),
        has_api_key=bool(API_KEY),
    )


@app.post("/api/preview", response_model=PreviewResponse, dependencies=[Depends(require_api_key)])
async def preview(
    pdfs: List[UploadFile] = File(...),
    excluded_domains: str = Form(""),
    excluded_emails: str = Form(""),
):
    pdf_paths = await _save_uploads(pdfs, prefix="list")
    domains = _split_csv(excluded_domains)
    emails = _split_csv(excluded_emails)
    counts = extract_emails_from_pdfs(pdf_paths, domains, emails, log=push_log)
    sent_before = load_sent_emails(DATA_DIR / "sent_emails.csv")
    new_list = sorted(e for e in counts if e not in sent_before)
    return PreviewResponse(
        total_found=len(counts),
        already_sent=len(sent_before),
        new_to_send=len(new_list),
        sample=new_list[:40],
    )


@app.post("/api/start", dependencies=[Depends(require_api_key)])
async def start(
    pdfs: List[UploadFile] = File(...),
    resume: UploadFile = File(...),
    subject: str = Form(DEFAULT_SUBJECT),
    body_html: str = Form(DEFAULT_BODY),
    reply_to: str = Form(""),
    dry_run: str = Form("false"),
    check_bounces: str = Form("true"),
    warmup_mode: str = Form("false"),
    batch_size: int = Form(50),
    daily_cap: Optional[int] = Form(None),
    excluded_domains: str = Form(""),
    excluded_emails: str = Form(""),
    # Optional override accounts from UI (still require API key). Format: email:pass;email2:pass2
    gmail_accounts: str = Form(""),
):
    global stop_requested
    with job_lock:
        if job_state["running"]:
            raise HTTPException(status_code=409, detail="A send job is already running.")

    dry = _as_bool(dry_run)
    bounces = _as_bool(check_bounces)
    warmup = _as_bool(warmup_mode)

    accounts = _parse_accounts_override(gmail_accounts) or parse_accounts_from_env()
    if not accounts and not dry:
        raise HTTPException(
            status_code=400,
            detail="No Gmail accounts. Set GMAIL_ACCOUNTS on the server or pass gmail_accounts.",
        )

    pdf_paths = await _save_uploads(pdfs, prefix="list")
    resume_path = await _save_one(resume, prefix="resume")
    reply = reply_to.strip() or (accounts[0]["email"] if accounts else "")

    cfg = SendConfig(
        accounts=accounts,
        reply_to=reply,
        subject=subject,
        body_html=body_html,
        pdf_paths=pdf_paths,
        attachment_path=str(resume_path),
        data_dir=DATA_DIR,
        mode="pdf",
        dry_run=dry,
        check_bounces=bounces and not dry,
        warmup_mode=warmup,
        batch_size=max(1, batch_size),
        daily_cap=daily_cap,
        excluded_domains=_split_csv(excluded_domains),
        excluded_emails=_split_csv(excluded_emails),
        stop_flag=lambda: stop_requested,
        on_progress=_on_progress,
        on_log=push_log,
    )

    _begin_job(cfg, dry)
    return {"ok": True, "mode": "pdf"}


@app.post("/api/manual/preview", response_model=PreviewResponse, dependencies=[Depends(require_api_key)])
async def manual_preview(
    emails_text: str = Form(""),
    csv_file: Optional[UploadFile] = File(None),
    excluded_domains: str = Form("squareboat.com,hudle.in,programming.com"),
    excluded_emails: str = Form("info@jobcurator.in"),
    daily_cap: int = Form(250),
    skip_already_sent: str = Form("true"),
):
    domains = _split_csv(excluded_domains)
    excluded = _split_csv(excluded_emails)
    recipients = parse_emails_from_text(emails_text, domains, excluded)
    if csv_file and csv_file.filename:
        csv_path = await _save_one(csv_file, prefix="manual_csv")
        from_csv = load_emails_from_csv(str(csv_path), domains, excluded, log=push_log)
        # merge preserving order
        seen = set(recipients)
        for e in from_csv:
            if e not in seen:
                recipients.append(e)
                seen.add(e)

    sent_before = load_sent_emails(DATA_DIR / "sent_emails.csv")
    skip = _as_bool(skip_already_sent)
    new_list = [e for e in recipients if e not in sent_before] if skip else list(recipients)
    sent_today = get_today_sent_count(DATA_DIR / "email_log.csv")
    remaining = max(0, daily_cap - sent_today)
    queued = new_list[:remaining]
    return PreviewResponse(
        total_found=len(recipients),
        already_sent=len(sent_before),
        new_to_send=len(queued),
        sample=queued[:40],
        sent_today=sent_today,
        remaining_today=remaining,
        mode="manual",
    )


@app.post("/api/manual/start", dependencies=[Depends(require_api_key)])
async def manual_start(
    resume: UploadFile = File(...),
    emails_text: str = Form(""),
    csv_file: Optional[UploadFile] = File(None),
    subject: str = Form(DEFAULT_SUBJECT),
    body_html: str = Form(DEFAULT_BODY),
    reply_to: str = Form(""),
    dry_run: str = Form("false"),
    check_bounces: str = Form("false"),
    warmup_mode: str = Form("false"),
    batch_size: int = Form(40),
    daily_cap: int = Form(250),
    max_per_hour: int = Form(55),
    skip_already_sent: str = Form("true"),
    excluded_domains: str = Form("squareboat.com,hudle.in,programming.com"),
    excluded_emails: str = Form("info@jobcurator.in"),
    gmail_accounts: str = Form(""),
):
    global stop_requested
    with job_lock:
        if job_state["running"]:
            raise HTTPException(status_code=409, detail="A send job is already running.")

    dry = _as_bool(dry_run)
    domains = _split_csv(excluded_domains)
    excluded = _split_csv(excluded_emails)
    recipients = parse_emails_from_text(emails_text, domains, excluded)
    if csv_file and csv_file.filename:
        csv_path = await _save_one(csv_file, prefix="manual_csv")
        from_csv = load_emails_from_csv(str(csv_path), domains, excluded, log=push_log)
        seen = set(recipients)
        for e in from_csv:
            if e not in seen:
                recipients.append(e)
                seen.add(e)

    if not recipients:
        raise HTTPException(status_code=400, detail="No valid emails found. Paste emails or upload a CSV.")

    accounts = _parse_accounts_override(gmail_accounts) or parse_accounts_from_env()
    if not accounts and not dry:
        raise HTTPException(
            status_code=400,
            detail="No Gmail accounts. Set GMAIL_ACCOUNTS on the server or pass gmail_accounts.",
        )

    resume_path = await _save_one(resume, prefix="resume")
    reply = reply_to.strip() or (accounts[0]["email"] if accounts else "")

    cfg = SendConfig(
        accounts=accounts,
        reply_to=reply,
        subject=subject,
        body_html=body_html,
        attachment_path=str(resume_path),
        data_dir=DATA_DIR,
        manual_emails=recipients,
        mode="manual",
        dry_run=dry,
        check_bounces=_as_bool(check_bounces) and not dry,
        warmup_mode=_as_bool(warmup_mode),
        batch_size=max(1, batch_size),
        daily_cap=daily_cap,
        max_per_hour=max(0, max_per_hour),
        skip_already_sent=_as_bool(skip_already_sent),
        respect_daily_log_cap=True,
        excluded_domains=domains,
        excluded_emails=excluded,
        stop_flag=lambda: stop_requested,
        on_progress=_on_progress,
        on_log=push_log,
    )

    _begin_job(cfg, dry)
    return {"ok": True, "mode": "manual", "queued_candidates": len(recipients)}


@app.post("/api/stop", dependencies=[Depends(require_api_key)])
def stop():
    global stop_requested
    if not job_state["running"]:
        return {"ok": False, "detail": "No job running"}
    stop_requested = True
    push_log("Stop requested from UI…")
    return {"ok": True}


def _begin_job(cfg: SendConfig, dry: bool) -> None:
    global stop_requested
    stop_requested = False
    with job_lock:
        job_state.update(
            running=True,
            phase="starting",
            mode=cfg.mode,
            total_found=0,
            already_sent=0,
            queued=0,
            sent=0,
            dry_run=dry,
            stopped=False,
            current=None,
            started_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            finished_at=None,
            error=None,
        )
    threading.Thread(target=_job_wrapper, args=(cfg,), daemon=True).start()


def _job_wrapper(cfg: SendConfig) -> None:
    try:
        run_send_job(cfg)
    except Exception as exc:
        push_log(f"Job failed: {exc}")
        with job_lock:
            job_state["error"] = str(exc)
            job_state["running"] = False
            job_state["phase"] = "error"
            job_state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")


def _on_progress(payload: dict) -> None:
    with job_lock:
        for key in (
            "running",
            "phase",
            "total_found",
            "already_sent",
            "queued",
            "sent",
            "dry_run",
            "stopped",
            "current",
            "mode",
        ):
            if key in payload:
                job_state[key] = payload[key]
        if not payload.get("running", True):
            job_state["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")


async def _save_uploads(files: List[UploadFile], prefix: str) -> List[str]:
    paths: List[str] = []
    for i, f in enumerate(files):
        paths.append(str(await _save_one(f, prefix=f"{prefix}_{i}")))
    return paths


async def _save_one(f: UploadFile, prefix: str) -> Path:
    name = Path(f.filename or "upload.bin").name
    dest = UPLOAD_DIR / f"{prefix}_{int(time.time())}_{name}"
    with dest.open("wb") as out:
        shutil.copyfileobj(f.file, out)
    return dest


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _split_csv(raw: str) -> Set[str]:
    return {p.strip().lower() for p in raw.split(",") if p.strip()}


def _parse_accounts_override(raw: str) -> List[dict]:
    accounts: List[dict] = []
    for part in (raw or "").split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        email, password = part.split(":", 1)
        accounts.append({"email": email.strip(), "password": password.strip()})
    return accounts


# ── Serve the mobile web UI from the SAME URL as the API ──────────────
# Registered last so /api/* keeps priority.
if FRONTEND_DIR.exists():

    @app.get("/")
    def ui_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{asset_path:path}")
    def ui_assets(asset_path: str):
        if asset_path.startswith("api/") or asset_path.startswith("docs") or asset_path.startswith("openapi"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (FRONTEND_DIR / asset_path).resolve()
        if not str(candidate).startswith(str(FRONTEND_DIR.resolve())):
            raise HTTPException(status_code=404, detail="Not found")
        if candidate.is_file():
            return FileResponse(candidate)
        raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
