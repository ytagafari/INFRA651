# INFRA651 — UCS CRM → Agent (clients_package knowledge base)

## Acceptance criteria

| AC | Implementation |
|----|----------------|
| CRM entry triggers agent with company/date/notes | Google Sheets + `crm/apps-script/CRM-Trigger.gs` → webhook |
| Agent retrieves docs by topic keywords | `agent/knowledge_retriever.py` → keyword + optional vector search |

## Quick start

```powershell
cd c:\Users\yt.agafari.UTILCELL\Desktop\INFRA651

# 1. Index clients_package folder into knowledge base
python scripts/import_clients_package.py

# 2. Optional — semantic vector search (recommended)
pip install -r requirements.txt
python scripts/build_embeddings.py

# 3. Run acceptance tests
python scripts/test_acceptance.py

# 3. Start webhook (CRM posts here)
python -m agent.webhook_server

# 4. Simulate CRM entry
curl -X POST http://localhost:8080/webhook/crm-opportunity ^
  -H "Content-Type: application/json" ^
  -H "X-Webhook-Secret: ucs-demo-secret" ^
  -d "@crm/sample-payload.json"
```

## Knowledge base source: `clients_package/`

All PDFs come from the **clients_package** folder:

| Folder | Contents |
|--------|----------|
| `datasheets/` | M740D, M740, WDESK-BL, Smart-Digital, CLM8 |
| `marketing/` | SensWEIGHT leaflets (silo, truck, belt, weighbridge) |
| `pricing/` | SensWEIGHT SaaS Pricing (€59–€299/device/month) |
| `certificates/` | CE / OIML R76, CLM8, Serie W |

Sheets index (for Google Drive): `knowledge-base/sheets/`

## Google Drive setup

1. Upload `knowledge-base/clients-package/` subfolders to Drive as **UCS-Knowledge-Base**
2. Import CSVs from `knowledge-base/sheets/` as Google Sheets
3. Import `crm/sheets/CRM-Opportunity-Notes.csv` as **CRM-Opportunity-Notes**
4. Bind Apps Script from `crm/apps-script/CRM-Trigger.gs`
5. Set `WEBHOOK_URL` (ngrok or hosted server) + `WEBHOOK_SECRET=ucs-demo-secret`
6. Run `createOnEditTrigger()`

## Vector search (semantic retrieval)

By default the agent uses **hybrid retrieval**: keyword matching + semantic vectors.

```powershell
pip install -r requirements.txt
python scripts/build_embeddings.py
```

| Setting | Default | Meaning |
|---------|---------|---------|
| `RETRIEVAL_MODE` | `hybrid` | `hybrid`, `keyword`, or `vector` |
| `RETRIEVAL_KEYWORD_WEIGHT` | `0.35` | Weight for exact keyword overlap |
| `RETRIEVAL_VECTOR_WEIGHT` | `0.65` | Weight for embedding similarity |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model |

Embeddings are cached in `knowledge-base/embeddings/`. Re-run `build_embeddings.py` after updating CSV indexes.

## Architecture

```
CRM Google Sheet (onEdit)
    → Apps Script POST {company, meeting_date, discussion_topics, notes}
    → Webhook /webhook/crm-opportunity
    → KnowledgeBase.retrieve(keywords + vectors)
    → clients_package PDFs + sheets index + embeddings
    → Agent brief saved to agent/runs/
```
