/**
 * CRM trigger: onEdit -> POST to agent webhook -> email follow-up to that row's sales rep.
 * Bind to CRM-Opportunity-Notes Google Sheet.
 *
 * Sheet columns (in order):
 *   timestamp | opportunity_id | company | meeting_date | sales_rep | sales_rep_email |
 *   discussion_topics | notes | status | last_updated
 *
 * Script properties: WEBHOOK_URL, WEBHOOK_SECRET, SEND_FOLLOWUP_EMAIL=true
 * Run once: createOnEditTrigger()
 */
const SHEET = 'CRM-Opportunity-Notes';
const COL = {
  COMPANY: 3,
  MEETING_DATE: 4,
  SALES_REP: 5,
  SALES_REP_EMAIL: 6,
  TOPICS: 7,
  NOTES: 8,
  UPDATED: 10,
};

function getConfig_() {
  const p = PropertiesService.getScriptProperties();
  const url = p.getProperty('WEBHOOK_URL');
  const secret = p.getProperty('WEBHOOK_SECRET');
  if (!url || !secret) throw new Error('Set WEBHOOK_URL and WEBHOOK_SECRET');
  return { url: url, secret: secret };
}

function buildPayload_(row) {
  return {
    event_type: 'opportunity_note_updated',
    timestamp: new Date().toISOString(),
    opportunity_id: String(row[1] || ''),
    company: String(row[COL.COMPANY - 1] || '').trim(),
    meeting_date: String(row[COL.MEETING_DATE - 1] || '').trim(),
    sales_rep: String(row[COL.SALES_REP - 1] || '').trim(),
    sales_rep_email: String(row[COL.SALES_REP_EMAIL - 1] || '').trim(),
    discussion_topics: String(row[COL.TOPICS - 1] || '').trim(),
    notes: String(row[COL.NOTES - 1] || '').trim(),
  };
}

function sendFollowUpEmail_(result, payload) {
  const enabled = (PropertiesService.getScriptProperties().getProperty('SEND_FOLLOWUP_EMAIL') || 'true')
    .toLowerCase() === 'true';
  if (!enabled) return;

  if (result.email_sent) {
    Logger.log('Email already sent by webhook to ' + result.email_sent_to);
    return;
  }

  const to = payload.sales_rep_email;
  if (!to) {
    Logger.log('Missing sales_rep_email for rep "' + (payload.sales_rep || '') + '" - email not sent');
    return;
  }

  const subject = result.email_subject || ('Follow-up: ' + payload.company);
  const body = result.email || 'No email body returned';
  const options = {};
  if (result.email_html) {
    options.htmlBody = result.email_html;
  }
  GmailApp.sendEmail(to, subject, body, options);
  Logger.log('Follow-up email sent to ' + to + ' (' + (payload.sales_rep || 'sales rep') + ')');
}

function postToAgent_(payload) {
  const cfg = getConfig_();
  const res = UrlFetchApp.fetch(cfg.url, {
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

function onEdit(e) {
  try {
    if (!e || !e.range) return;
    const sh = e.range.getSheet();
    if (sh.getName() !== SHEET || e.range.getRow() <= 1) return;
    const row = sh.getRange(e.range.getRow(), 1, 1, COL.UPDATED).getValues()[0];
    const payload = buildPayload_(row);
    if (!payload.company || !payload.meeting_date || !payload.discussion_topics) return;
    sh.getRange(e.range.getRow(), COL.UPDATED).setValue(new Date().toISOString());
    const result = postToAgent_(payload);
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
}

function testSendSampleRow() {
  const payload = {
    company: 'AgriScale GmbH',
    meeting_date: '2026-06-12',
    sales_rep: 'Jan Novak',
    sales_rep_email: 'jan.novak@unifiedcloudsensors.eu',
    discussion_topics: 'SensSILO, silo monitoring, agriculture, pricing, SaaS subscription',
    notes: '38 grain silos - wants SensWEIGHT silo leaflet and SaaS pricing',
  };
  const result = postToAgent_(payload);
  sendFollowUpEmail_(result, payload);
  Logger.log('Sent to: ' + payload.sales_rep_email);
}

function testSendEmailToNikola() {
  const payload = {
    company: 'Bruto',
    meeting_date: '2026-06-09',
    sales_rep: 'Nikola',
    sales_rep_email: 'nikola@unifiedcloudsensors.eu',
    contact_name: 'Milo\u0161',
    discussion_topics: 'Laumas, UCS-X3, DiniArgeo, camera system, Modbus, certificate, pricing, marketing, Slovakia, scales',
    notes: 'Bruto Laumas M500. ~10 scales/year Slovakia.',
    extra_news: 'We have just ordered calibration confirmation stickers - placed on the scale after each calibration.',
  };
  const result = postToAgent_(payload);
  sendFollowUpEmail_(result, payload);
  Logger.log('Sent to: ' + payload.sales_rep_email);
}
