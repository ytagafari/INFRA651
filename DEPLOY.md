# Deploy UCS CRM Agent (optional — for 24/7 webhook without ngrok)

You **do not need deploy** for the assignment. Use this when you want a **permanent URL** so Google Sheets works without your PC + ngrok.

---

## Can you change things after deploy?

**Yes.** What you can edit and how:

| What you change | How | Redeploy needed? |
|-----------------|-----|------------------|
| CRM Google Sheet rows | Edit sheet | No |
| Apps Script `WEBHOOK_SECRET` | Script properties | No (must match cloud env) |
| Apps Script `WEBHOOK_URL` | Script properties | No |
| Product/doc keywords (`Document-Index.csv`) | Edit CSV → git push | **Yes** (or rebuild on host) |
| PDFs in `clients_package` | Replace files → push | **Yes** |
| Webhook Python code | Edit → git push | **Yes** (auto on Render if connected to GitHub) |
| Secret `CRM_WEBHOOK_SECRET` | Render dashboard → Environment | Restart only |
| Google Drive PDFs | Upload in Drive | No (Drive is separate from webhook) |

**Rule:** Code and files on the server → redeploy. Google Sheets / Drive / Apps Script URL → change anytime in browser.

---

## Option A — Render.com (recommended, free tier)

### Prerequisites

1. GitHub account  
2. Push `INFRA651` to a GitHub repo (include `clients_package`, `knowledge-base`, `agent`, `scripts`, `crm`)  
3. Account at https://render.com  

### Steps

1. **Push code to GitHub**
   ```powershell
   cd c:\Users\yt.agafari.UTILCELL\Desktop\INFRA651
   git init
   git add .
   git commit -m "UCS CRM agent"
   git remote add origin https://github.com/YOUR_USER/INFRA651.git
   git push -u origin main
   ```

2. **Create Web Service on Render**
   - Dashboard → **New +** → **Web Service**
   - Connect your GitHub repo `INFRA651`
   - Settings:
     | Field | Value |
     |-------|--------|
     | **Runtime** | Python 3 |
     | **Build Command** | `pip install -r requirements.txt && python scripts/import_clients_package.py && python scripts/build_embeddings.py` |
     | **Start Command** | `python -m agent.webhook_server` |
     | **Instance type** | Free |

3. **Environment variables** (Render → Environment)
   | Key | Value |
   |-----|--------|
   | `CRM_WEBHOOK_SECRET` | `ucs-demo-secret` (or your own secret) |
   | `WEBHOOK_HOST` | `0.0.0.0` |

4. **Deploy** → wait for **Live**

5. **Your permanent URL** (example):
   ```
   https://ucs-crm-agent.onrender.com
   ```

6. **Test health**
   ```powershell
   Invoke-RestMethod -Uri "https://ucs-crm-agent.onrender.com/health"
   ```

7. **Update Google Apps Script**
   | Property | Value |
   |----------|--------|
   | `WEBHOOK_URL` | `https://ucs-crm-agent.onrender.com/webhook/crm-opportunity` |
   | `WEBHOOK_SECRET` | same as `CRM_WEBHOOK_SECRET` |

   Remove ngrok header if you want (optional on Render — no browser warning):
   ```javascript
   // ngrok-skip-browser-warning not needed on Render
   ```

8. Run **`testSendSampleRow`** in Apps Script.

### Render free tier notes

- Service **sleeps** after ~15 min idle — first request may take 30–60 s (cold start)
- Free URL **does not change** (unlike ngrok)
- **Edit & redeploy:** push to GitHub → Render auto-redeploys

---

## Option B — Keep PC + ngrok (no deploy)

| Pros | Cons |
|------|------|
| No GitHub/cloud setup | PC must be on |
| Already working locally | ngrok URL changes on restart (free) |

Good for **assignment demo only**.

---

## Option C — Railway / Fly.io / VPS

Same idea as Render:

1. Upload repo  
2. Build: `python scripts/import_clients_package.py`  
3. Start: `python -m agent.webhook_server`  
4. Set env `CRM_WEBHOOK_SECRET`  
5. Use assigned HTTPS URL in Apps Script  

---

## After deploy — update workflow

### Change knowledge base (new PDFs / keywords)

```powershell
# 1. Edit files locally
#    - clients_package/...
#    - or knowledge-base/sheets/Document-Index.csv

# 2. Re-index
python scripts/import_clients_package.py

# 3. Commit & push (Render auto-deploys)
git add .
git commit -m "Update knowledge base"
git push
```

### Change webhook code

Edit `agent/*.py` → commit → push → Render redeploys.

### Change CRM only

Edit Google Sheet — **no redeploy**.

### Change webhook URL in Google

Only if you create a **new** Render service or rename URL — update `WEBHOOK_URL` in Script properties.

---

## Security checklist for production

- [ ] Use a **strong** `CRM_WEBHOOK_SECRET` (not `ucs-demo-secret`)
- [ ] Do **not** commit `.env` to GitHub  
- [ ] Add `.gitignore` with `.env`, `agent/runs/`, `__pycache__/`

---

## Quick comparison

| | Local + ngrok | Render deploy |
|--|---------------|---------------|
| Permanent URL | No | Yes |
| PC must run | Yes | No |
| Edit code | Save file, restart | Git push, auto redeploy |
| Cost | Free | Free tier |
| Assignment | Enough | Stronger demo |

---

## Minimum files needed in GitHub repo

```
INFRA651/
├── agent/
├── clients_package/          ← must be in repo for cloud build
├── crm/
├── knowledge-base/sheets/    ← optional if import runs from clients_package
├── scripts/import_clients_package.py
├── requirements.txt
└── render.yaml               ← optional blueprint
```

Do **not** upload secrets. Set `CRM_WEBHOOK_SECRET` only in Render dashboard.
