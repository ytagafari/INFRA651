/**
 * UCS CRM — SINGLE FILE for Google Apps Script
 * Paste this ENTIRE file into Code.gs ONLY.
 * Delete all other .gs files (CRM-Trigger, Email-Sender, duplicates).
 *
 * Script properties (Project Settings → Script properties):
 *   WEBHOOK_URL          = https://YOUR-NGROK-URL/webhook/crm-opportunity
 *   WEBHOOK_SECRET       = ucs-demo-secret
 *   SEND_FOLLOWUP_EMAIL  = true
 *   EMAIL_WEBHOOK_SECRET = ucs-email-secret   (optional, for Web App email)
 *
 * Run once: createOnEditTrigger()
 * Test:      testSendEmailToNikola()
 * Gmail test: testSendDirect()
 *
 * Optional Web App deploy (Deploy → Web app): uses doPost() below for Python .env GMAIL_WEBAPP_URL
 */

// ─── CRM Sheet trigger ───────────────────────────────────────────────────────

var CRM_SHEET = 'CRM-Opportunity-Notes';
var CRM_COL = {
  COMPANY: 3,
  MEETING_DATE: 4,
  SALES_REP: 5,
  SALES_REP_EMAIL: 6,
  TOPICS: 7,
  NOTES: 8,
  UPDATED: 10,
};

function getConfig_() {
  var p = PropertiesService.getScriptProperties();
  var url = p.getProperty('WEBHOOK_URL');
  var secret = p.getProperty('WEBHOOK_SECRET');
  if (!url || !secret) throw new Error('Set WEBHOOK_URL and WEBHOOK_SECRET in Script properties');
  return { url: url, secret: secret };
}

function buildPayload_(row) {
  return {
    event_type: 'opportunity_note_updated',
    timestamp: new Date().toISOString(),
    opportunity_id: String(row[1] || ''),
    company: String(row[CRM_COL.COMPANY - 1] || '').trim(),
    meeting_date: String(row[CRM_COL.MEETING_DATE - 1] || '').trim(),
    sales_rep: String(row[CRM_COL.SALES_REP - 1] || '').trim(),
    sales_rep_email: String(row[CRM_COL.SALES_REP_EMAIL - 1] || '').trim(),
    discussion_topics: String(row[CRM_COL.TOPICS - 1] || '').trim(),
    notes: String(row[CRM_COL.NOTES - 1] || '').trim(),
  };
}

function postToAgent_(payload) {
  var cfg = getConfig_();
  var res = UrlFetchApp.fetch(cfg.url, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'X-Webhook-Secret': cfg.secret,
      'ngrok-skip-browser-warning': '1',
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });
  if (res.getResponseCode() >= 300) throw new Error(res.getContentText());
  return JSON.parse(res.getContentText());
}

function sendFollowUpEmail_(result, payload) {
  var enabled = (PropertiesService.getScriptProperties().getProperty('SEND_FOLLOWUP_EMAIL') || 'true')
    .toLowerCase() === 'true';
  if (!enabled) return;

  if (result.email_sent) {
    Logger.log('Email already sent by webhook to ' + result.email_sent_to);
    return;
  }

  var to = payload.sales_rep_email;
  if (!to) {
    Logger.log('Missing sales_rep_email - email not sent');
    return;
  }

  var subject = result.email_subject || ('Follow-up: ' + payload.company);
  var body = result.email || 'No email body returned';
  var options = {};
  if (result.email_html) {
    options.htmlBody = result.email_html;
  }
  GmailApp.sendEmail(to, subject, body, options);
  Logger.log('Follow-up email sent to ' + to);
}

function onEdit(e) {
  try {
    if (!e || !e.range) return;
    var sh = e.range.getSheet();
    if (sh.getName() !== CRM_SHEET || e.range.getRow() <= 1) return;
    var row = sh.getRange(e.range.getRow(), 1, 1, CRM_COL.UPDATED).getValues()[0];
    var payload = buildPayload_(row);
    if (!payload.company || !payload.meeting_date || !payload.discussion_topics) return;
    sh.getRange(e.range.getRow(), CRM_COL.UPDATED).setValue(new Date().toISOString());
    var result = postToAgent_(payload);
    sendFollowUpEmail_(result, payload);
  } catch (err) {
    console.error(err);
  }
}

function createOnEditTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'onEdit') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('onEdit').forSpreadsheet(SpreadsheetApp.getActive()).onEdit().create();
  Logger.log('onEdit trigger created');
}

function testSendSampleRow() {
  var payload = {
    company: 'AgriScale GmbH',
    meeting_date: '2026-06-12',
    sales_rep: 'Jan Novak',
    sales_rep_email: 'jan.novak@unifiedcloudsensors.eu',
    discussion_topics: 'SensSILO, silo monitoring, agriculture, pricing, SaaS subscription',
    notes: '38 grain silos - wants SensWEIGHT silo leaflet and SaaS pricing',
  };
  var result = postToAgent_(payload);
  sendFollowUpEmail_(result, payload);
  Logger.log('Done. Sent to: ' + payload.sales_rep_email);
}

function testSendEmailToNikola() {
  var payload = {
    company: 'Bruto',
    meeting_date: '2026-06-09',
    sales_rep: 'Nikola',
    sales_rep_email: 'yt.agafari@unifiedcloudsensors.com',
    contact_name: 'Milo\u0161',
    input_summary: [
      'Summary',
      'On June 9, 2026, a meeting took place between Miloš, a colleague, and Nikola, where they discussed the Laumas system and a camera system.',
      'Key Points',
      '📅 Meeting Date: June 9, 2026',
      '💻 Implementation: Laumas and UCS-X3 on DiniArgeo',
      '📷 Camera System: Focus on SW implementation, not selling HW',
      '📄 Required Information: Certificate D, price list, marketing materials',
      '📈 Potential: Miloš sees a potential of 10 scales per year, but needs help with clients in Slovakia',
    ].join('\n'),
    discussion_topics: 'Laumas, UCS-X3, DiniArgeo, camera, certificate, pricing, Slovakia',
    notes: 'Bruto Laumas M500. ~10 scales/year Slovakia.',
  };
  var result = postToAgent_(payload);
  sendFollowUpEmail_(result, payload);
  Logger.log('Done. Check Executions log and inbox: ' + payload.sales_rep_email);
}

// ─── Optional: Web App email endpoint (for Python GMAIL_WEBAPP_URL) ───────────

function doPost(e) {
  try {
    var expected = PropertiesService.getScriptProperties().getProperty('EMAIL_WEBHOOK_SECRET');
    var data = JSON.parse(e.postData.contents);
    if (!expected || data.secret !== expected) {
      return jsonResponse_(401, { error: 'unauthorized' });
    }
    if (!data.to || !data.subject || !data.body) {
      return jsonResponse_(400, { error: 'Missing to, subject, or body' });
    }
    var options = {};
    if (data.html) {
      options.htmlBody = String(data.html);
    }
    if (data.attachments && data.attachments.length) {
      options.attachments = data.attachments.map(function (a) {
        return Utilities.newBlob(
          Utilities.base64Decode(String(a.content)),
          String(a.mimeType || 'application/pdf'),
          String(a.filename)
        );
      });
    }
    GmailApp.sendEmail(String(data.to), String(data.subject), String(data.body), options);
    return jsonResponse_(200, { sent: true, to: data.to });
  } catch (err) {
    return jsonResponse_(500, { error: String(err) });
  }
}

function jsonResponse_(code, body) {
  body.httpCode = code;
  return ContentService.createTextOutput(JSON.stringify(body)).setMimeType(
    ContentService.MimeType.JSON
  );
}

function testSendDirect() {
  var email = Session.getActiveUser().getEmail();
  GmailApp.sendEmail(email, 'UCS test email', 'GmailApp works.');
  Logger.log('Test sent to ' + email);
}
