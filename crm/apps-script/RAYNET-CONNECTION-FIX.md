# RAYNET "Connection to the server failed" — fix

## Why RAYNET shows this error (important)

RAYNET **URL TEST** often sends **HEAD** request.

Google Apps Script **always returns 403 for HEAD** — you cannot fix this in code.

| Test type | Google Apps Script | RAYNET result |
|-----------|-------------------|---------------|
| HEAD (RAYNET URL test) | **403 Forbidden** | "Connection failed" |
| GET (browser open URL) | **200 OK** | Works |
| POST (real webhook) | **200** | Works |

**Your automation can still work even when URL TEST fails.**

You already had `doPost` executions in Apps Script — that proves POST works.

---

## Step 1 — Use the correct URL in RAYNET

1. Apps Script → **Deploy → Manage deployments**
2. Copy **Web app URL** (ends with `/exec`)
3. Add secret at the end:

```
https://script.google.com/macros/s/YOUR_ID/exec?secret=ucs-demo-secret
```

4. Paste into RAYNET webhook URL field

---

## Step 2 — Test in browser (not RAYNET URL test)

1. Open **Incognito** window
2. Paste your URL (with `?secret=ucs-demo-secret`)
3. You must see plain text: **OK**

If you see error **"doGet not found"** → old deployment. Redeploy with latest code.

---

## Step 3 — Deploy settings (required)

| Field | Value |
|-------|--------|
| Execute as | **Me** |
| Who has access | **Anyone** (NOT "Anyone with Google account") |

Then: **New version → Deploy**

---

## Step 4 — Skip RAYNET URL TEST

1. In RAYNET webhook settings, **ignore** "Connection failed" on URL TEST
2. Click **SAVE** anyway
3. Turn automation **ON**
4. Edit a meeting → **SAVE**
5. Check Google Sheet tab **Webhook-Log**

If a new row appears → connection works.

---

## Step 5 — Wrong URL checklist

| Symptom | Fix |
|---------|-----|
| Browser shows "doGet not found" | Paste latest `Raynet-Agent.gs`, redeploy new version |
| Browser shows Google login page | Set access to **Anyone** |
| Browser shows 403 | Wrong deployment or Workspace blocks public apps |
| URL TEST fails but browser shows OK | **Normal** — skip URL test, save webhook |
| No Webhook-Log row after meeting save | Automation OFF or conditions not met |

---

## Workspace policy (if browser also fails)

If **Incognito browser** does not show OK, your IT may block public Google Apps Script web apps.

Ask IT to allow public web app deployments, or use a different host for the webhook.
