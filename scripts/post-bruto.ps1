# Post Bruto meeting payload to local webhook (UTF-8 safe on Windows PowerShell)
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$body = Get-Content (Join-Path $root "crm\bruto-meeting.json") -Raw -Encoding UTF8

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8080/webhook/crm-opportunity" `
  -Method POST `
  -Headers @{
    "Content-Type" = "application/json; charset=utf-8"
    "X-Webhook-Secret" = "ucs-demo-secret"
  } `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
