# Mailer Desk

`No_Limit.py` logic as a **Python FastAPI backend**, plus a **static frontend** you can host for free with **no credit card**.

```
mailer/
  backend/     ← FastAPI (SMTP send, PDF extract, dual Gmail, bounce check)
  frontend/    ← static HTML/CSS/JS (Cloudflare Pages / GitHub Pages)
```

Your original `No_Limit.py` is unchanged and still works as a CLI.

---

## Free hosting (₹0, no card)

| Piece | Where | Card needed? |
|--------|--------|----------------|
| **Frontend** | [Cloudflare Pages](https://pages.cloudflare.com/) or [GitHub Pages](https://pages.github.com/) | No |
| **Backend** | [PythonAnywhere](https://www.pythonanywhere.com/) free, or your laptop + [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) | No |

SMTP + long send jobs cannot run on GitHub/Cloudflare Pages. Keep the API on PythonAnywhere or your machine.

---

## 1) Run backend locally

```bash
cd mailer/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export GMAIL_ADDRESS="you@gmail.com"
export GMAIL_APP_PASSWORD="your gmail app password"
export API_KEY="pick-a-long-random-secret"
export CORS_ORIGINS="*"

python main.py
# → http://127.0.0.1:8000
# docs → http://127.0.0.1:8000/docs
```

Gmail: enable 2FA → create an [App Password](https://myaccount.google.com/apppasswords).

---

## 2) Frontend (local)

Open `mailer/frontend/index.html` in a browser, **or**:

```bash
cd mailer/frontend
python3 -m http.server 5500
# → http://127.0.0.1:5500
```

In the UI:

1. Set **API URL** → `http://127.0.0.1:8000`
2. Set **API Key** → same as `API_KEY`
3. Click **Save** (green health dot = backend reachable)
4. Upload job-list PDF(s) + resume → **Preview** → **Start sending**

---

## 3) Deploy frontend free (Cloudflare Pages)

1. Create a free Cloudflare account (no card).
2. **Workers & Pages → Create → Pages → Upload assets**
3. Upload the contents of `mailer/frontend/` (`index.html`, `styles.css`, `app.js`)
4. After deploy, open the `*.pages.dev` URL and set **API URL** to your backend.

### Or GitHub Pages

1. Push `mailer/frontend/` to a repo (or `/docs`).
2. Settings → Pages → Deploy from branch.
3. Open the `*.github.io` URL and point **API URL** at your backend.

---

## 4) Deploy backend free (PythonAnywhere)

1. Sign up at [pythonanywhere.com](https://www.pythonanywhere.com/) (free Beginner — no card).
2. Upload `mailer/backend/` (Files tab) or clone your repo.
3. In a Bash console:

```bash
cd ~/mailer/backend
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Web → Add a new web app → **Manual configuration** → Python 3.10.
5. Set source/working directory to `mailer/backend`.
6. WSGI file example:

```python
import sys, os
project = "/home/YOUR_USERNAME/mailer/backend"
if project not in sys.path:
    sys.path.insert(0, project)
os.environ["GMAIL_ADDRESS"] = "you@gmail.com"
os.environ["GMAIL_APP_PASSWORD"] = "xxxx xxxx xxxx xxxx"
os.environ["API_KEY"] = "your-secret"
os.environ["CORS_ORIGINS"] = "https://YOUR_FRONTEND.pages.dev"
from main import app as application
```

7. Reload the web app. Free tier sleeps when idle; fine for personal use.

**Note:** PythonAnywhere free outbound SMTP to Gmail is often allowed; if blocked, run the backend on your laptop and expose it with Cloudflare Tunnel (also free, no card):

```bash
# after backend is running on :8000
cloudflared tunnel --url http://127.0.0.1:8000
```

Paste the `https://….trycloudflare.com` URL into the frontend **API URL**.

---

## Security

- Do **not** commit Gmail app passwords. Use env vars / host secrets.
- Set a strong `API_KEY` before putting the frontend on the public internet.
- Rotate any app passwords that were previously hardcoded in `No_Limit.py` / `ui.py`.

---

## Modes in the UI

| Tab | Same as | Recipients |
|-----|---------|------------|
| **PDF lists** | `No_Limit.py` | Extract from uploaded PDFs |
| **Manual emails** | `EmailManual.py` | Paste list and/or CSV (`Email` column) |

Manual mode defaults: batch 40, max 55/hour, daily cap 250, respects today's send count.

## API quick reference

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Public ping |
| GET | `/api/status` | Job + live log |
| POST | `/api/preview` | Extract emails from PDFs |
| POST | `/api/start` | Start PDF send / dry-run |
| POST | `/api/manual/preview` | Preview pasted / CSV emails |
| POST | `/api/manual/start` | Start manual send / dry-run |
| POST | `/api/stop` | Request stop |

All routes except `/api/health` require header `X-API-Key` when `API_KEY` is set.
