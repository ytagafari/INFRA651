# Google Drive / Sheets Setup (clients_package)

## Folder structure in Google Drive

Create **UCS-Knowledge-Base** and upload from `knowledge-base/clients-package/`:

```
UCS-Knowledge-Base/
├── datasheets/       ← 5 PDFs (M740D, M740, WDESK-BL, Smart-Digital, CLM8)
├── marketing/        ← 7 SensWEIGHT + SensVibra leaflets
├── pricing/          ← SaaS pricing + truck scale offers (+ ROI video)
├── certificates/     ← CE / OIML R76 / CLM8 approvals
└── (root videos)     ← ROI_of_IoT_Monitoring.mp4, etc.
```

## Google Sheets (import CSVs)

Import from `knowledge-base/sheets/`:

| CSV | Sheet name |
|-----|------------|
| Product-Catalog.csv | Product-Catalog |
| Document-Index.csv | Document-Index |
| Price-List.csv | Price-List |
| Applications.csv | Applications |
| CRM-Opportunity-Notes.csv | CRM-Opportunity-Notes |

**Document-Index** links each PDF to keywords — the agent uses this for retrieval.

## CRM automation

1. Open **CRM-Opportunity-Notes** sheet
2. **Extensions → Apps Script** → paste `crm/apps-script/CRM-Trigger.gs`
3. Script properties:
   - `WEBHOOK_URL` = your public webhook (ngrok or server)
   - `WEBHOOK_SECRET` = `ucs-demo-secret`
4. Run **`createOnEditTrigger()`**
5. Add row with **company**, **meeting_date**, **discussion_topics**

## Acceptance criteria demo

**Test row:**
| company | meeting_date | discussion_topics |
|---------|--------------|-------------------|
| AgriScale GmbH | 2026-06-12 | SensSILO, silo monitoring, agriculture, pricing, SaaS |

**Expected agent docs:**
- SensWEIGHT Silo Leaflet (`MKT-SW-SILO`)
- SensWEIGHT SaaS Pricing (`PL-SW-SAAS`) — €59–€299/device/month

Run locally first:
```powershell
python scripts/import_clients_package.py
python scripts/test_acceptance.py
python -m agent.webhook_server
```
