# RAYNET meeting → Gmail draft (each field)

Your webhook sends **empty** `workflow.event` data. The script now **falls back to RAYNET API** and loads the **latest edited meeting**.

## Required — Script properties

| Property | Value |
|----------|--------|
| `RAYNET_USER` | API username from RAYNET → API Keys |
| `RAYNET_API_KEY` | API key |
| `RAYNET_INSTANCE` | `ucs` |
| `DRAFT_EMAIL` | yt.agafari@unifiedcloudsensors.com |
| `WEBHOOK_SECRET` | ucs-demo-secret |

## Gmail draft shows

- Account (company)
- Subject
- Date from / Date to
- Questions to Discuss
- Meeting outcome (Solution)
- Contact, Owner, Location
- Meeting ID

## Steps

1. Paste `Raynet-Agent.gs` → Save → **Deploy New version** (Execute as Me)
2. Add Script properties above
3. Save a meeting in RAYNET calendar
4. Open **Gmail → Drafts**

## Optional — fix webhook (so API fallback not needed)

Automation → Send webhook → map keys: `company`, `discussion_topics`, `description`, `meeting_date`, `meeting_id`
