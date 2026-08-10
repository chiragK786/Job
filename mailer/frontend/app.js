const DEFAULT_SUBJECT =
  "QA Automation Engineer / SDET — 4 Years of Experience in Test Automation & CI/CD Integration";

const DEFAULT_BODY = `<p>Dear Hiring Manager,</p>
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
<p>Warm regards,<br><strong>Chirag Khanduja</strong><br>QA Automation Engineer | SDET<br>903-422-6868</p>`;

const $ = (id) => document.getElementById(id);

let currentMode = localStorage.getItem("mailer_mode") || "pdf";

function loadCfg() {
  $("apiUrl").value = localStorage.getItem("mailer_api_url") || "http://127.0.0.1:8000";
  $("apiKey").value = localStorage.getItem("mailer_api_key") || "";
  $("subject").value = localStorage.getItem("mailer_subject") || DEFAULT_SUBJECT;
  $("body").value = localStorage.getItem("mailer_body") || DEFAULT_BODY;
  setMode(currentMode, false);
}

function saveCfg() {
  localStorage.setItem("mailer_api_url", $("apiUrl").value.trim().replace(/\/$/, ""));
  localStorage.setItem("mailer_api_key", $("apiKey").value.trim());
  localStorage.setItem("mailer_subject", $("subject").value);
  localStorage.setItem("mailer_body", $("body").value);
  localStorage.setItem("mailer_mode", currentMode);
  showError("");
  pingHealth();
}

function apiBase() {
  return ($("apiUrl").value || "").trim().replace(/\/$/, "");
}

function headers() {
  const h = {};
  const key = $("apiKey").value.trim();
  if (key) h["X-API-Key"] = key;
  return h;
}

function showError(msg) {
  const el = $("formError");
  if (!msg) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = msg;
}

function setMode(mode, persist = true) {
  currentMode = mode === "manual" ? "manual" : "pdf";
  if (persist) localStorage.setItem("mailer_mode", currentMode);

  document.querySelectorAll(".mode-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === currentMode);
  });

  const isManual = currentMode === "manual";
  $("pdfFields").hidden = isManual;
  $("manualFields").hidden = !isManual;
  $("pdfDailyCapWrap").hidden = isManual;
  $("skipSentWrap").hidden = !isManual;
  $("modeHint").textContent = isManual
    ? "Paste emails or upload CSV (EmailManual flow — hourly limit + daily cap)."
    : "Extract recipients from job-list PDFs (No_Limit flow).";

  $("batchSize").value = isManual ? "40" : "50";
  $("checkBounces").checked = !isManual;
  showError("");
}

function appendCommonFields(fd) {
  fd.append("subject", $("subject").value);
  fd.append("body_html", $("body").value);
  fd.append("reply_to", $("replyTo").value.trim());
  fd.append("dry_run", $("dryRun").checked ? "true" : "false");
  fd.append("check_bounces", $("checkBounces").checked ? "true" : "false");
  fd.append("warmup_mode", $("warmup").checked ? "true" : "false");
  fd.append("batch_size", $("batchSize").value || (currentMode === "manual" ? "40" : "50"));
  fd.append("excluded_domains", $("excludedDomains").value);
  fd.append("excluded_emails", $("excludedEmails").value);
  if ($("gmailAccounts").value.trim()) {
    fd.append("gmail_accounts", $("gmailAccounts").value.trim());
  }
}

function buildPdfFormData() {
  const fd = new FormData();
  const pdfs = $("pdfs").files;
  if (!pdfs.length) throw new Error("Select at least one job-list PDF.");
  for (const f of pdfs) fd.append("pdfs", f);

  const resume = $("resume").files[0];
  if (!resume) throw new Error("Select a resume PDF attachment.");
  fd.append("resume", resume);

  appendCommonFields(fd);
  if ($("dailyCap").value) fd.append("daily_cap", $("dailyCap").value);
  return fd;
}

function buildManualFormData({ includeResume = true } = {}) {
  const fd = new FormData();
  const text = $("emailsText").value.trim();
  const csv = $("csvFile").files[0];
  if (!text && !csv) throw new Error("Paste emails or upload a CSV file.");
  fd.append("emails_text", text);
  if (csv) fd.append("csv_file", csv);

  if (includeResume) {
    const resume = $("resume").files[0];
    if (!resume) throw new Error("Select a resume PDF attachment.");
    fd.append("resume", resume);
  }

  appendCommonFields(fd);
  fd.append("daily_cap", $("manualDailyCap").value || "250");
  fd.append("max_per_hour", $("maxPerHour").value || "55");
  fd.append("skip_already_sent", $("skipAlreadySent").checked ? "true" : "false");
  return fd;
}

function fillPreview(data) {
  $("sFound").textContent = data.total_found;
  $("sSentBefore").textContent = data.already_sent;
  $("sQueued").textContent = data.new_to_send;
  if (data.sent_today != null) $("sSentToday").textContent = data.sent_today;
  const ul = $("sampleList");
  ul.innerHTML = "";
  (data.sample || []).forEach((email) => {
    const li = document.createElement("li");
    li.textContent = email;
    ul.appendChild(li);
  });
  const rem =
    data.remaining_today != null ? ` · ${data.remaining_today} left under daily cap` : "";
  $("currentLine").textContent = `Preview ready — ${data.new_to_send} recipients${rem}.`;
}

async function preview() {
  showError("");
  try {
    let url;
    let fd;
    if (currentMode === "manual") {
      url = `${apiBase()}/api/manual/preview`;
      fd = buildManualFormData({ includeResume: false });
    } else {
      url = `${apiBase()}/api/preview`;
      fd = new FormData();
      const pdfs = $("pdfs").files;
      if (!pdfs.length) throw new Error("Select at least one job-list PDF.");
      for (const f of pdfs) fd.append("pdfs", f);
      fd.append("excluded_domains", $("excludedDomains").value);
      fd.append("excluded_emails", $("excludedEmails").value);
    }

    const r = await fetch(url, { method: "POST", headers: headers(), body: fd });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(formatDetail(data) || `Preview failed (${r.status})`);
    fillPreview(data);
  } catch (err) {
    showError(err.message || String(err));
  }
}

async function startSend() {
  showError("");
  try {
    saveCfg();
    const url =
      currentMode === "manual"
        ? `${apiBase()}/api/manual/start`
        : `${apiBase()}/api/start`;
    const fd =
      currentMode === "manual" ? buildManualFormData({ includeResume: true }) : buildPdfFormData();

    const r = await fetch(url, { method: "POST", headers: headers(), body: fd });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(formatDetail(data) || `Start failed (${r.status})`);
    $("btnStart").disabled = true;
    $("btnStop").disabled = false;
    $("currentLine").textContent = `Job started (${currentMode})…`;
  } catch (err) {
    showError(err.message || String(err));
  }
}

function formatDetail(data) {
  if (!data) return "";
  if (typeof data.detail === "string") return data.detail;
  if (data.detail) return JSON.stringify(data.detail);
  return "";
}

async function stopSend() {
  try {
    const r = await fetch(`${apiBase()}/api/stop`, {
      method: "POST",
      headers: headers(),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || "Stop failed");
    $("currentLine").textContent = "Stop requested…";
  } catch (err) {
    showError(err.message || String(err));
  }
}

function renderStatus(d) {
  const job = d.job || {};
  const badge = $("phaseBadge");
  const phase = job.phase || (job.running ? "sending" : "idle");
  const modeTag = job.mode ? ` · ${job.mode}` : "";
  badge.textContent = phase + modeTag;
  badge.className = "badge" + (job.running ? " on" : job.phase === "error" ? " err" : "");

  if (job.total_found != null) $("sFound").textContent = job.total_found;
  if (job.already_sent != null) $("sSentBefore").textContent = job.already_sent;
  if (job.queued != null) $("sQueued").textContent = job.queued;
  $("sSentNow").textContent = job.sent ?? 0;
  $("sAccounts").textContent = d.accounts_configured ?? "–";

  const queued = Number(job.queued) || 0;
  const sent = Number(job.sent) || 0;
  const pct = queued ? Math.min(100, Math.round((sent / queued) * 100)) : 0;
  $("progressBar").style.width = `${pct}%`;

  $("btnStart").disabled = !!job.running;
  $("btnStop").disabled = !job.running;

  if (job.current) {
    $("currentLine").textContent = `Sending → ${job.current}`;
  } else if (job.error) {
    $("currentLine").textContent = `Error: ${job.error}`;
  } else if (job.finished_at && !job.running) {
    $("currentLine").textContent =
      `Finished at ${job.finished_at}` + (job.stopped ? " (stopped)" : "");
  }

  const logEl = $("log");
  const atBottom = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 24;
  logEl.textContent = (d.log || []).join("\n");
  if (atBottom) logEl.scrollTop = logEl.scrollHeight;
}

async function poll() {
  if (!apiBase()) return;
  try {
    const r = await fetch(`${apiBase()}/api/status`, { headers: headers() });
    if (!r.ok) return;
    const d = await r.json();
    renderStatus(d);
  } catch {
    /* ignore */
  }
}

async function pingHealth() {
  const dot = $("healthDot");
  try {
    const r = await fetch(`${apiBase()}/api/health`);
    dot.className = "dot " + (r.ok ? "ok" : "bad");
  } catch {
    dot.className = "dot bad";
  }
}

document.querySelectorAll(".mode-tab").forEach((btn) => {
  btn.addEventListener("click", () => setMode(btn.dataset.mode));
});

$("btnSaveCfg").addEventListener("click", saveCfg);
$("btnPreview").addEventListener("click", preview);
$("btnStart").addEventListener("click", startSend);
$("btnStop").addEventListener("click", stopSend);

loadCfg();
pingHealth();
poll();
setInterval(poll, 2000);
setInterval(pingHealth, 15000);
