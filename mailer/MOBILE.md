# Use Mailer Desk from your phone (anywhere, ₹0)

Goal: **one bookmark on your phone** — open it from home, office, metro — send emails. No laptop needed after setup.

## Best free option: Koyeb (usually no credit card)

### 1) One-time setup (laptop, ~10 min)

1. Create a free account: [https://app.koyeb.com](https://app.koyeb.com)  
   (Card only if their fraud check asks — most accounts skip it.)
2. **Create Web Service** → import GitHub repo `chiragK786/Job`
3. Settings:
   - **Branch:** `mailer-pages`
   - **Builder:** Dockerfile
   - **Dockerfile location:** `mailer/Dockerfile`
   - **Work directory:** `mailer` (if asked)
   - Instance: **Free / Nano**
4. **Environment variables** (Secrets):

| Key | Value |
|-----|--------|
| `GMAIL_ADDRESS` | your Gmail |
| `GMAIL_APP_PASSWORD` | Gmail App Password |
| `API_KEY` | any long random string (optional but recommended) |
| `CORS_ORIGINS` | `*` |
| `PORT` | `8000` |

5. Deploy → copy your public URL, like:  
   `https://mailer-desk-xxxx.koyeb.app`

### 2) Phone

1. Open that **Koyeb URL** in Chrome / Safari  
2. Add to Home Screen (optional)  
3. If you set `API_KEY`, open **Server** → paste key → Save  
4. Green **online** → upload / paste emails → Send  

API URL leave **blank** (same website = backend).

### Keep-awake tip

Free Koyeb sleeps after ~1 hour idle. Opening the app on your phone wakes it (first load may take a few seconds). While a send job runs and the page stays open, status polling keeps it awake.

---

## Gmail App Password

Google Account → Security → 2-Step Verification → App passwords → Mail.

---

## GitHub Pages?

`https://chiragk786.github.io/Job/` is UI-only. For anywhere-mobile, prefer the **Koyeb URL** (UI + API together). Or on GitHub Pages set Server → API URL = your Koyeb link.
