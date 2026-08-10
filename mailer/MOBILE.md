# Mobile se kahin bhi use (₹0, no card)

**Koyeb mat use karo** — naye accounts pe free band ho chuka hai (sirf paid).  
**Render free** use karo.

## 1) Render account
1. Open [https://dashboard.render.com/register](https://dashboard.render.com/register)
2. **Sign up with GitHub** (card mat add karna)
3. GitHub authorize karo → repo `Job` access do

## 2) New Web Service
1. [https://dashboard.render.com/](https://dashboard.render.com/) → **New +** → **Web Service**
2. Connect repo: **`chiragK786/Job`**
3. Settings:

| Field | Value |
|--------|--------|
| Name | `mailer-desk` |
| Branch | `mailer-pages` |
| Root Directory | `mailer` |
| Runtime | **Docker** |
| Instance type | **Free** |
| Health Check Path | `/api/health` |

4. **Environment** (Add):

| Key | Value |
|-----|--------|
| `GMAIL_ADDRESS` | your Gmail |
| `GMAIL_APP_PASSWORD` | Gmail App Password |
| `API_KEY` | `klkBADBglT7w_5rNVYx5uIImpss4i_XN` |
| `CORS_ORIGINS` | `*` |
| `PORT` | `8000` |

5. **Create Web Service** → wait for Build + Live (3–7 min)

URL milega: `https://mailer-desk-xxxx.onrender.com`

## 3) Phone
1. Usi Render URL ko open / Home Screen pe add karo  
2. **Server** → API Key paste → Save  
3. API URL **blank**  
4. Pehli baar 30–60 sec lag sakta hai (free sleep) — phir green **online**

## Tip
Free Render 15 min idle pe so jata hai. App open karte hi wake up ho jata hai.
