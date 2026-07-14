# Get RAYNET meeting details in Gmail — step by step

Use **`Raynet-Agent.gs`** (not the simplified Sheet1 script). It loads **full meeting fields from the RAYNET API** and creates a **Gmail draft** with every field on its own line.

---

## Overview

```
RAYNET: edit meeting → SAVE
  → Automation sends webhook POST
  → Apps Script doPost()
  → RAYNET API GET /meeting/{id}/  (full details)
  → Gmail draft + Webhook-Log row
```

---

## STEP 1 — Google Sheet (one time)

1. Open **UCS-Knowledge-Base** spreadsheet.
2. Apps Script → **Extensions → Apps Script** (or open the bound script project).
3. Run **`saveSpreadsheetId_`** once (Run ▶).
4. Execution log should show: `Saved SPREADSHEET_ID: ...`

---

## STEP 2 — Paste the correct code (one time)

1. In Apps Script, **delete** your simplified `Sheet1` script (the one with `HEADERS` / `testDoPostManually` fake payload).
2. Keep **one file**: copy all of **`Raynet-Agent.gs`** from this repo into the editor.
3. Optional second file: **`Raynet-Raw-Logger.gs`** only if you want debug tabs `Webhook-Raw` + `Meeting-API`.
4. Keep **`appsscript.json`** with Gmail + external_request scopes (already in repo).

---

## STEP 3 — Script properties (one time)

Apps Script → **Project settings** (gear) → **Script properties** → Add:

| Property | Value |
|----------|--------|
| `WEBHOOK_SECRET` | `ucs-demo-secret` |
| `DRAFT_EMAIL` | `yt.agafari@unifiedcloudsensors.com` |
| `RAYNET_USER` | `n.avramovic@unifiedcloudsensors.com` |
| `RAYNET_API_KEY` | your full `crm-...` key |
| `RAYNET_INSTANCE` | `ucs` |

Run **`showSetupStatus()`** — log must show `RAYNET API: OK`.

---

## STEP 4 — Deploy web app (every code change)

1. **Deploy → New deployment**
2. Type: **Web app**
3. Execute as: **Me** (`yt.agafari@unifiedcloudsensors.com`)
4. Who has access: **Anyone**
5. Deploy → copy **Web app URL**

Your URL must end with:

```
?secret=ucs-demo-secret
```

Example:

```
https://script.google.com/macros/s/AKfycb.../exec?secret=ucs-demo-secret
```

6. Open that URL in a browser → must show: **`OK — webhook ready...`**

---

## STEP 5 — RAYNET automation webhook (recommended path)

### 5a — Register webhook (gear icon)

1. RAYNET → **Settings → Automations** (or Automations list).
2. Open **Automation webhooks** (gear ⚙).
3. **Delete** old webhooks that had hardcoded test text (e.g. "Calender Meeting Tracker").
4. **Add new webhook**:
   - Name: `UCS-Meeting-Live`
   - URL: paste full Apps Script URL **with** `?secret=ucs-demo-secret`
   - **No** field mapping on this screen — URL only.

### 5b — Automation rule

1. Create or edit automation:
   - **Trigger:** Meeting is edited
   - **Action:** Send webhook → choose `UCS-Meeting-Live`
2. Map body keys (use `{ }` picker, **not** typed text):

| Key | RAYNET field |
|-----|----------------|
| `webhook_secret` | type text: `ucs-demo-secret` |
| `company` | Meeting → Account |
| `discussion_topics` | Meeting → Subject |
| `description` | Meeting → Questions to Discuss |
| `meeting_date` | Meeting → Date from |

3. Turn automation **ON** (green).
4. Remove extra conditions while testing.

---

## STEP 6 — Test without RAYNET (Apps Script)

Run these in order:

| Function | What it proves |
|----------|----------------|
| `showSetupStatus()` | API credentials + sheet OK |
| `pullDraftFromRaynet()` | API + Gmail draft works |
| `testWebhookLocally()` | Full pipeline (webhook shape + API match) |

Then open **Gmail → Drafts** (account that deployed the app — **Execute as Me**).

---

## STEP 7 — Live test in RAYNET

1. Open any **calendar meeting** in RAYNET.
2. Change **Subject** (e.g. add `-TEST-88`).
3. Click green **SAVE** (do not only close the popup).
4. Within ~60 seconds:
   - Apps Script → **Executions** → new `doPost` run
   - Sheet **Webhook-Log** → new row, `status=OK`, `draft=YES`
   - **Gmail → Drafts** → email with all meeting fields

Run **`whereIsMyDraft()`** if anything is missing.

---

## STEP 8 — What the Gmail draft contains

Subject line example: `RAYNET Meeting — AgriScale Task trail`

Body includes (each on its own line):

- Subject, Status, Scheduled from/to, Duration
- Account, Contact, Owner, Participants
- Questions to Discuss, Meeting outcome
- Meeting ID, Data source

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Browser URL shows UNAUTHORIZED | Add `?secret=ucs-demo-secret` to URL |
| Executions empty | Automation OFF, wrong webhook URL, or meeting not saved |
| `UNAUTHORIZED` in log | Add `webhook_secret=ucs-demo-secret` in Send webhook body |
| Draft empty / `no_fields` | Set RAYNET API script properties; run `pullDraftFromRaynet()` |
| Wrong meeting | Webhook sends static test text — delete old webhook, recreate URL-only |
| No draft in your inbox | Drafts are under **deployer account** (Execute as Me), not `DRAFT_EMAIL` sender — `DRAFT_EMAIL` is the **To** address |
| `HTTP 401` on API | Fix `RAYNET_USER` / `RAYNET_API_KEY` / `RAYNET_INSTANCE=ucs` |

---

## Optional — OpenAPI webhook (`PUT /api/v2/webhook/`)

Only use **one** webhook system (automation **or** OpenAPI), not both.

OpenAPI sends only `entityId` — script fetches full meeting via API.

Register URL **must** include `?secret=ucs-demo-secret` (Apps Script cannot read `X-RAYNETCRM-Token` header).

```powershell
curl.exe -X PUT "https://app.raynet.cz/api/v2/webhook/" `
  -H "X-Instance-Name: ucs" `
  -H "Content-Type: application/json" `
  -u "n.avramovic@unifiedcloudsensors.com:YOUR_CRM_KEY" `
  -d "{\"url\":\"YOUR_APPS_SCRIPT_URL?secret=ucs-demo-secret\",\"events\":[\"record.updated\"],\"secretToken\":\"ucs-demo-secret\"}"
```

Test in Apps Script: **`testRecordUpdatedWebhook()`** (change `entityId` to a real meeting id).

---

## Checklist (print this)

- [ ] `Raynet-Agent.gs` pasted (not simplified Sheet1 script)
- [ ] Script properties set (5 keys)
- [ ] Web app deployed — Execute as Me, Anyone
- [ ] URL opens with `OK` in browser
- [ ] `UCS-Meeting-Live` webhook — URL only, no static test body
- [ ] Automation maps `webhook_secret`, `company`, `discussion_topics`, `description`, `meeting_date`
- [ ] Automation ON
- [ ] `pullDraftFromRaynet()` → draft in Gmail
- [ ] Edit meeting → SAVE → draft + Webhook-Log row
