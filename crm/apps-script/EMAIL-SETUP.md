# Why setupOnce sends email but RAYNET doPost does not

| | setupOnce | RAYNET webhook |
|---|-----------|----------------|
| Runs as | You (editor) | Web app deployment |
| Includes `webhook_secret` | Yes (in code) | Often **missing** in RAYNET mapping |
| Result if secret wrong | N/A | **UNAUTHORIZED** — no email |

---

## Fix in 2 minutes

### Fix 1 — Add secret to webhook URL (easiest)

Your Apps Script URL looks like:

```
https://script.google.com/macros/s/AKfycb...../exec
```

Change it in RAYNET to:

```
https://script.google.com/macros/s/AKfycb...../exec?secret=ucs-demo-secret
```

RAYNET → Automation → Step 3 → **Webhook URL** → paste URL with `?secret=ucs-demo-secret` at end → **SAVE**

### Fix 2 — Deploy settings

Deploy → Manage deployments → Edit:

| Field | Must be |
|-------|---------|
| Execute as | **Me** |
| Who has access | **Anyone** |

Version → **New version** → Deploy

### Fix 3 — Paste updated Raynet-Agent.gs

Copy latest file → Apps Script → Save → redeploy (new version)

---

## Check Webhook-Log tab after meeting save

| status | Meaning | Fix |
|--------|---------|-----|
| **UNAUTHORIZED** | Secret missing | Fix 1 above |
| **NO_TOPICS** | Subject not mapped | Key `discussion_topics` → RAYNET Subject |
| **NO_EMAIL** | Gmail blocked | Redeploy as Execute as **Me** |
| **OK** | Success | Check Gmail inbox/spam |

---

## RAYNET webhook keys

| Key (type exactly) | RAYNET field |
|--------------------|--------------|
| `discussion_topics` | Subject |
| `webhook_secret` | fixed text: `ucs-demo-secret` |
| `company` | Account |
| `meeting_date` | Date from |

Email always goes to **yt.agafari@unifiedcloudsensors.com**
