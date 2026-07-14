# RAYNET API setup — reliable meeting date

When the webhook sends the wrong date (e.g. July 2 instead of the calendar **Date from**), the script can call the **RAYNET REST API** directly and read `scheduledFrom` from the meeting record.

No Apps Script **Libraries** or **Services (+)** are required — only `UrlFetchApp` (already built in).

---

## Overview

```
RAYNET meeting saved
  → Webhook includes meeting_id
  → Apps Script GET /api/v2/meeting/{id}/
  → scheduledFrom = true calendar date
  → Gmail draft uses that date
```

---

## Part 1 — Get RAYNET API credentials (5 min)

**Where:** [app.raynet.cz](https://app.raynet.cz) → **Settings** (gear) → **API access** (or **Integrations → API**)

You need these values from **Settings → API access**:

| What | Example | **NOT this** |
|------|---------|--------------|
| **Instance name** | `unifiedcloudsensors` or `my-company` | ~~`Agent Integration`~~ (that is the integration label) |
| **Instance ID** | `12673ba842c44fc0bb1596dd63ef0dbb` | optional alternative to instance name |
| **API user** | `api@company.rnt` | |
| **API key** | long secret string | |

### How to find the correct instance name (do not guess)

**Method A — Browser URL (easiest)**

1. Log into RAYNET in Chrome
2. Copy the full URL from the address bar, e.g.:
   ```
   https://app.raynet.cz/utilcell/?view=DashboardView
                           ^^^^^^^^^
                           this is your instance name
   ```
3. Set Script property `RAYNET_LOGIN_URL` to that full URL
4. Run **`discoverRaynetApiSetup()`** in Apps Script — it finds the correct instance + API region automatically

**Method B — About dialog**

1. In RAYNET, click **your name** (top menu)
2. Click **About Raynet CRM**
3. Copy the **Instance name** shown in the dialog
4. Set `RAYNET_INSTANCE` to that value **exactly** (case-sensitive)

**Method C — Instance ID**

On the API access page, if you see a UUID **Instance ID**, set `RAYNET_INSTANCE_ID` instead of guessing the name.

**Wrong values (do not use):**

| Wrong | Why |
|-------|-----|
| `Agent Integration` | Integration label, not instance |
| `unifiedcloudsensors` | Your email domain ≠ instance name |

**Docs:** [RAYNET CRM API](https://app.raynet.cz/api/doc/index-en.html)

### Create API credentials (fixes HTTP 401)

**Where:** RAYNET → **Settings** → **For Developers** → **API Keys**  
(Czech: **Nastavení** → **Pro vývojáře** → **API klíče**)

1. Create a new **API user** (or open existing)
2. Generate / copy the **API key** (shown **once** — save it immediately)
3. Note the **API username** (often looks like `something@....rnt`)

| Script property | Value |
|-----------------|--------|
| `RAYNET_USER` | API **username** from step 3 |
| `RAYNET_API_KEY` | API **key** from step 2 |

**Do NOT use:**

| Wrong | Use instead |
|-------|-------------|
| Your normal RAYNET login email | Dedicated API username |
| Your RAYNET password | API key string |
| Webhook secret `ucs-demo-secret` | Separate API key from API Keys page |

Run **`showRaynetApiCredentialsHelp()`** in Apps Script if you get HTTP 401.

---

## Part 2 — Add Script properties in Apps Script (2 min)

**Where:** UCS-Knowledge-Base sheet → **Extensions → Apps Script** → **Project Settings** (gear) → **Script properties** → **Add script property**

Add these **four** properties:

| Property | Value |
|----------|--------|
| `RAYNET_INSTANCE` | Instance **short name** from API settings (no spaces) |
| `RAYNET_INSTANCE_ID` | *(optional)* Instance UUID — use **instead of** `RAYNET_INSTANCE` if name fails |
| `RAYNET_USER` | API username |
| `RAYNET_API_KEY` | API key |
| `RAYNET_TEST_MEETING_ID` | One meeting ID for testing (see Part 4) |
| `RAYNET_LOGIN_URL` | Full RAYNET browser URL (for `discoverRaynetApiSetup`) |

Optional:

| Property | Value |
|----------|--------|
| `RAYNET_API_URL` | Only if not using `https://app.raynet.cz/api/v2` |

---

## Part 3 — Add meeting ID to RAYNET webhook (3 min)

**Where:** RAYNET → **Settings → Automations** → your meeting automation → **Send webhook** step

Add this row to the webhook body:

| Key (type exactly) | RAYNET field |
|--------------------|--------------|
| **`meeting_id`** | **ID** (meeting record ID) |

Keep your existing mappings:

| Key | RAYNET field |
|-----|--------------|
| `scheduledFrom` | **Date from** |
| `meeting_date` | **Date from** |
| `meeting_report` | **Questions to Discuss** |
| `discussion_topics` | **Subject** |
| `company` | **Account** |
| `webhook_secret` | fixed text: `ucs-demo-secret` |

**SAVE** the automation.

---

## Part 4 — Find a meeting ID for testing

**Where:** RAYNET → **Calendar** → open a meeting

The meeting ID is usually in the URL when you open the meeting detail, e.g.:

```
https://app.raynet.cz/.../meeting/12345/...
                              ^^^^^
```

Put that number in Script property `RAYNET_TEST_MEETING_ID`.

---

## Part 5 — Update code and redeploy (3 min)

1. Copy latest **`Raynet-Agent.gs`** into Apps Script → **Save**
2. **Deploy → Manage deployments → Edit → New version → Deploy**
3. First run will ask for **external URL** permission (UrlFetch to RAYNET) — **Allow**

---

## Part 6 — Test

### Test A — Auto-discover instance (if connection fails)

1. Log into RAYNET → copy browser URL
2. Set `RAYNET_LOGIN_URL` = that URL
3. Run **`discoverRaynetApiSetup`**
4. Copy the values it prints into Script properties
5. Run **`testRaynetApiConnection`**

### Test B — Connection only

Select **`testRaynetApiConnection`** → **Run**

Expected:

```
OK — RAYNET API credentials and instance are correct.
```

### Test C — Meeting date

Select **`testRaynetApi`** → **Run**

1. Edit and save a meeting in RAYNET
2. Open **Webhook-Log** tab in Google Sheet
3. Last row `detail` should include:

```
date=2026-07-08 src=raynet_api meeting_id=12345
```

4. Open **Gmail → Drafts** — opening line should show the correct calendar date

### Test C — Diagnostics

Run **`diagnoseAll`** — should show:

```
RAYNET API: configured
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Instance not found: Agent Integration` | **Wrong instance** — change `RAYNET_INSTANCE` to the short code from API settings, NOT "Agent Integration" |
| `RAYNET API: NOT set` | Add script properties in Part 2 |
| HTTP 401 | Wrong API user/key — use **API Keys** page, not login password (see below) |
| HTTP 404 (meeting) | Wrong `RAYNET_TEST_MEETING_ID` |
| `src=webhook` not `raynet_api` | Add `meeting_id` → **ID** in webhook body (Part 3) |
| Permission error on first run | Approve UrlFetch external request |
| Date still wrong | Redeploy **new version** after pasting latest code |

---

## Priority order (how date is chosen)

| Order | Source | When |
|-------|--------|------|
| 1 | **raynet_api** | API configured + `meeting_id` in webhook |
| 2 | **scheduledFrom** | Calendar field in webhook payload |
| 3 | **webhook** | `meeting_date` key in webhook |
| 4 | **notes_text** | Date written in Questions to Discuss |

---

## Security note

Store `RAYNET_API_KEY` only in **Script properties** — never in the Google Sheet or webhook body.
