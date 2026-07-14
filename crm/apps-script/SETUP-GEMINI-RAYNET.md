# INFRA-651 Updated — RAYNET + Drive + Apps Script + Gemini

Meeting report in RAYNET → Apps Script agent → **Gemini** picks documents → email with Google Drive links.

---

## Architecture

```
RAYNET CRM (meeting report in Solution field)
  → Automation webhook POST
  → Apps Script doPost()  ← agent
  → Gemini API (Google AI Studio)  ← picks doc_ids
  → Google Sheet (Document-Index + Drive-Links)
  → Google Drive PDF links
  → Gmail follow-up
```

---

## TASK 1 — Google Drive (PDF storage)

**Where:** [drive.google.com](https://drive.google.com)

1. Create folder **UCS-Knowledge-Base**
2. Upload PDFs (datasheets, marketing, pricing, certificates)
3. Each PDF → **Share → Anyone with link → Viewer** (or share with your Google account)

**Done when:** PDFs visible in Drive folder.

---

## TASK 2 — Google Sheet (document index)

**Where:** Google Drive → New → Google Sheet → name **UCS-Knowledge-Base**

1. Import `knowledge-base/sheets/Document-Index.csv` → tab **Document-Index**
2. Import `knowledge-base/sheets/Drive-Links.csv` → tab **Drive-Links**
3. **Drive-Links:** column A = `doc_id`, column B = **Drive file ID** (from PDF URL)

Example file ID from `https://drive.google.com/file/d/ABC123xyz/view` → `ABC123xyz`

**Done when:** Both tabs exist with data.

---

## TASK 3 — Google AI Studio (Gemini API key)

**Where:** [aistudio.google.com](https://aistudio.google.com)

1. Sign in with your Google account
2. Click **Get API key** (left menu)
3. **Create API key** → copy key (starts with `AIza...`)
4. Keep it secret — you paste it in Apps Script only

**Done when:** You have a Gemini API key copied.

---

## TASK 4 — Apps Script agent (with Gemini)

**Where:** UCS-Knowledge-Base sheet → **Extensions → Apps Script**

1. Delete old / simplified code (Sheet1-only script)
2. Paste all of **`Raynet-Agent.gs`** (includes meeting fetch + Gemini + PDF attachments)
3. **Save**
4. **Project Settings** (gear) → **Script properties** → Add:

| Property | Value |
|----------|--------|
| `GEMINI_API_KEY` | your `AIza...` key |
| `USE_GEMINI` | `true` |
| `DRAFT_EMAIL` | yt.agafari@unifiedcloudsensors.com |
| `WEBHOOK_SECRET` | ucs-demo-secret |
| `RAYNET_USER` | n.avramovic@unifiedcloudsensors.com |
| `RAYNET_API_KEY` | your `crm-...` key |
| `RAYNET_INSTANCE` | ucs |

5. Run **`saveSpreadsheetId_`** (with UCS-Knowledge-Base sheet open)
6. Run **`setupOnce`** → Authorize (Gmail + Drive + external requests)
7. Run **`testGemini`** → check log for `doc_ids` like `MKT-SW-SILO`, `PL-SW-SAAS`
8. Check **Gmail → Drafts** — draft should have PDF attachments
9. **Deploy → Manage deployments → Edit**
   - Execute as: **Me**
   - Who has access: **Anyone**
   - **New version → Deploy**
10. Copy Web app URL + add: `?secret=ucs-demo-secret`

**Done when:** `testGemini` creates draft with PDFs; browser URL shows **OK**.

---

## TASK 5 — RAYNET automation (meeting report input)

**Where:** [app.raynet.cz](https://app.raynet.cz) → Settings → Automations

### 5A — Register webhook (if not done)

Settings → Automations → gear → **Automation webhook** → create **UCS meeting notes** → SAVE

### 5B — Create automation

| Step | Setting |
|------|---------|
| **Trigger** | Meeting → **Meeting is edited** |
| **Condition 1** | Account **is filled in** |
| **Condition 2** | **Solution** **is filled in** (meeting report) |
| **Action** | **Send webhook** → select **UCS meeting notes** |

### 5C — Webhook URL

```
https://script.google.com/macros/s/YOUR_ID/exec?secret=ucs-demo-secret
```

Ignore RAYNET URL TEST "connection failed" — save anyway.

### 5D — Key/Value body (type keys exactly)

| Key | RAYNET field |
|-----|--------------|
| `company` | **Account** |
| `meeting_date` | **Date from** |
| `discussion_topics` | **Subject** |
| `description` | **Questions to Discuss** |
| `meeting_report` | **Solution** (meeting outcome — used by Gemini for email text) |
| `meeting_id` | **ID** (if available — best accuracy) |
| `webhook_secret` | fixed: `ucs-demo-secret` |

**Important:** RAYNET only sends fields you map here. If `company` or `meeting_date` is missing from the webhook body, the draft email will say "Unknown company" / "our recent meeting".

After saving a meeting, run **`inspectLastWebhook`** in Apps Script or check **Webhook-Log** → column **Detail** → look for `mapped=co=... date=... WARN=...`

**SAVE** → turn automation **ON**

---

## TASK 6 — Sales rep workflow (daily use)

**Where:** RAYNET → Calendar → Meeting

1. Link **Account**
2. Write **meeting report** in **Solution**
3. **SAVE**
4. Check **Gmail → Drafts** — AI follow-up email with **PDF attachments**

---

## TASK 8 — Drive PDF access (required for attachments)

Apps Script attaches PDFs using **Drive file IDs** from the **Drive-Links** sheet.

1. PDFs must live in Google Drive (upload `knowledge-base/clients-package/` PDFs)
2. Each PDF → **Share** with the account that deploys the web app (`yt.agafari@...`) — at least **Viewer**
3. **Drive-Links** column B = file ID from URL `https://drive.google.com/file/d/FILE_ID/view`

Without Drive access, the draft email still works but PDFs won't attach (links in body only).

---

## TASK 7 — Verify

| Check | Where | Expected |
|-------|--------|----------|
| Webhook-Log | Google Sheet tab | status **OK**, retrieval **gemini** |
| Executions | Apps Script | `doPost` completed |
| Gmail | Inbox | Follow-up with doc links |
| Gemini test | Run `testGemini` | MKT-SW-SILO, PL-SW-SAAS for AgriScale report |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Gemini error | Check `GEMINI_API_KEY` in Script properties |
| Wrong docs | Improve keywords in Document-Index sheet |
| No email | See EMAIL-SETUP.md |
| UNAUTHORIZED | Add `?secret=ucs-demo-secret` to URL |
| Falls back to keywords | Gemini failed — check Executions log; keyword search still runs |
