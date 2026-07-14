# RAYNET calendar → Webhook-Log — complete setup (every field)

When you **edit and save** a meeting in [app.raynet.cz](https://app.raynet.cz), this flow logs **each calendar field** and creates a Gmail draft.

```
RAYNET calendar (edit meeting → Save)
    → Automation webhook (key/value body + meeting_id)
    → Apps Script doPost()
    → RAYNET REST API GET /meeting/{id}/  (fills any missing fields)
    → Webhook-Log row (company, subject, date, questions, raw_json, api)
    → Gmail Draft
```

---

## Calendar fields → what you get

| RAYNET calendar field (UI) | API field | Webhook key | Webhook-Log column |
|----------------------------|-----------|-------------|-------------------|
| **Account** | `company.name` | `company` | **company** |
| **Subject** | `title` | `discussion_topics` | **subject** |
| **Questions to Discuss** | `description` | `description` | **questions** |
| **Date from** | `scheduledFrom` | `meeting_date` | **meeting_date** |
| **Solution** (optional) | `solution` | `meeting_report` | (fallback for questions) |
| **Contact** | `person.fullName` | `contact_name` | in **raw_json** |
| **Owner** | `owner.fullName` | — | in **raw_json** |
| **Meeting ID** | `id` | `meeting_id` | **detail** + API fetch |

---

# PART 1 — Google Apps Script (10 min)

**Where:** UCS-Knowledge-Base sheet → **Extensions → Apps Script**

| Step | Action |
|------|--------|
| 1 | Paste latest **`Raynet-Agent.gs`** → **Save** |
| 2 | **Project Settings** (gear) → **Script properties** → add:

| Property | Value |
|----------|--------|
| `FALLBACK_EMAIL` | yt.agafari@unifiedcloudsensors.com |
| `WEBHOOK_SECRET` | ucs-demo-secret |
| `GEMINI_API_KEY` | *(optional)* your `AIza...` key |
| `USE_GEMINI` | `true` *(optional)* |

| 3 | Run **`setupOnce`** → authorize Gmail + external requests |
| 4 | **Deploy → Manage deployments → Edit** |
| | Execute as: **Me** |
| | Who has access: **Anyone** |
| | Version: **New version** → **Deploy** |
| 5 | Copy Web App URL → add at end: `?secret=ucs-demo-secret` |

**Done when:** `testDraftOnly` creates a draft in Gmail.

---

# PART 2 — RAYNET API credentials (10 min)

**Why:** Webhook mapping can miss fields. With API + `meeting_id`, the script reads the **full calendar record** after every save.

**Where:** RAYNET → **Settings** → **For Developers** → **API Keys**

| Step | Action |
|------|--------|
| 1 | Create API user → copy **API username** (e.g. `api@....rnt`) |
| 2 | Generate **API key** (shown once — save it) |
| 3 | Find **instance name** — browser URL: `https://app.raynet.cz/YOUR_INSTANCE/...` |
| 4 | *(Alternative)* **About Raynet CRM** → copy Instance name |
| 5 | Add Script properties:

| Property | Value |
|----------|--------|
| `RAYNET_USER` | API username from step 1 |
| `RAYNET_API_KEY` | API key from step 2 |
| `RAYNET_INSTANCE` | Instance short name (e.g. `utilcell`) |
| `RAYNET_LOGIN_URL` | Full browser URL while logged in *(for discovery)* |
| `RAYNET_TEST_MEETING_ID` | One meeting ID for testing (Part 4) |

| 6 | Run **`discoverRaynetApiSetup`** if instance name is wrong |
| 7 | Run **`testRaynetApiConnection`** → expect `OK` |
| 8 | Run **`testRaynetMeetingFields`** → prints every calendar field |

**Never put API key in the Google Sheet or webhook body.**

---

# PART 3 — RAYNET automation webhook (10 min)

**Where:** RAYNET → **Settings → Automations**

## 3A — Register webhook (once)

Settings → Automations → gear → **Automation webhook** → create **UCS meeting notes** → SAVE

## 3B — Create automation

| Setting | Value |
|---------|--------|
| **Trigger** | Meeting → **Meeting is edited** |
| **Condition** | Account **is filled in** |
| **Action** | **Send webhook** → UCS meeting notes |

## 3C — Webhook URL

```
https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec?secret=ucs-demo-secret
```

Ignore RAYNET “connection failed” on URL test — **save anyway**.

## 3D — Webhook body keys (type exactly)

| Key | RAYNET field |
|-----|--------------|
| **`meeting_id`** | **ID** ← required for API to fetch all fields |
| `company` | **Account** |
| `meeting_date` | **Date from** |
| `discussion_topics` | **Subject** |
| `description` | **Questions to Discuss** |
| `scheduledFrom` | **Date from** *(backup)* |
| `webhook_secret` | fixed: `ucs-demo-secret` |

**SAVE** → turn automation **ON**

---

# PART 4 — Find meeting ID

**Where:** RAYNET → **Calendar** → open a meeting

URL contains the ID:

```
https://app.raynet.cz/.../meeting/5991/...
                              ^^^^
```

Put `5991` in Script property `RAYNET_TEST_MEETING_ID`.

---

# PART 5 — Sales rep workflow (daily)

| Step | Where | What |
|------|-------|------|
| 1 | RAYNET Calendar | Open meeting |
| 2 | Fill **Account**, **Subject**, **Questions to Discuss**, **Date from** |
| 3 | **Save** | Triggers webhook |
| 4 | Gmail | Open **Drafts** (not Inbox) |
| 5 | Google Sheet | **Webhook-Log** tab — new row with all columns |

---

# PART 6 — Verify each field

## A — Apps Script tests

| Run this | Expect |
|----------|--------|
| `testRaynetApiConnection` | OK — credentials correct |
| `testRaynetMeetingFields` | Lists company, subject, questions, date |
| `inspectLastWebhook` | Last row with all columns |
| `viewLastRaynetInput` | Each key RAYNET sent |
| `showWhatIsLeft` | ✅/❌ checklist |

## B — Webhook-Log columns (after save)

| Column | Should contain |
|--------|----------------|
| company | Your Account name |
| subject | Meeting Subject |
| meeting_date | `2026-07-08` |
| questions | Full Questions to Discuss text |
| parsed_keys | `meeting_id, company, description, ...` |
| raw_json | Full webhook JSON |
| detail | `sources=company=api date=api ...` |

## C — Field source priority

| Field | Order |
|-------|--------|
| Any field | 1) Webhook value (if sent) → 2) RAYNET API (if `meeting_id` + API configured) |
| Date | 1) RAYNET API → 2) scheduledFrom → 3) meeting_date → 4) text in notes |

---

# PART 7 — Troubleshooting

| Problem | Fix |
|---------|-----|
| Webhook-Log empty | Automation OFF or wrong URL — add `?secret=ucs-demo-secret` |
| status UNAUTHORIZED | Add `webhook_secret` key or URL secret |
| company = Unknown | Map `company` → Account; add `meeting_id` → ID |
| date empty | Map `meeting_date` → Date from; configure API |
| questions empty | Map `description` → Questions to Discuss |
| `api_err=HTTP 401` | Wrong `RAYNET_USER` / `RAYNET_API_KEY` — use API Keys page |
| `Instance not found` | Run `discoverRaynetApiSetup` with `RAYNET_LOGIN_URL` |
| Draft not in Inbox | Normal — check **Gmail → Drafts** |
| `sources=` all webhook | API not configured or `meeting_id` missing from webhook |

---

# Quick reference — Script properties

| Property | Required | Purpose |
|----------|----------|---------|
| `WEBHOOK_SECRET` | Yes | Match RAYNET webhook |
| `FALLBACK_EMAIL` | Yes | Draft recipient |
| `RAYNET_USER` | For API | API username |
| `RAYNET_API_KEY` | For API | API key |
| `RAYNET_INSTANCE` | For API | CRM instance name |
| `RAYNET_TEST_MEETING_ID` | For tests | Test meeting ID |
| `RAYNET_LOGIN_URL` | For discovery | Browser URL |
| `GEMINI_API_KEY` | Optional | Smarter PDF selection |

---

# Security

- API key → **Script properties only**
- Webhook secret → URL `?secret=` + body `webhook_secret`
- Never commit credentials to git or Google Sheet cells
