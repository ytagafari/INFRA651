/**
 * RAYNET calendar meeting → Gmail draft (each field listed)
 *
 * Script properties:
 *   WEBHOOK_SECRET      ucs-demo-secret
 *   DRAFT_EMAIL         yt.agafari@unifiedcloudsensors.com
 *   RAYNET_USER         API username (required if webhook sends empty data)
 *   RAYNET_API_KEY      API key
 *   RAYNET_INSTANCE     ucs
 *   GEMINI_API_KEY      AIza... (Google AI Studio)
 *   USE_GEMINI          true
 *   GEMINI_MODEL        gemini-2.0-flash (optional)
 *
 * Sheet tabs: Document-Index, Drive-Links (import CSVs from knowledge-base/sheets/)
 * URL: .../exec?secret=ucs-demo-secret
 */

var LOG_SHEET = 'Webhook-Log';
var DOC_SHEET = 'Document-Index';
var LINKS_SHEET = 'Drive-Links';
var DEFAULT_SECRET = 'ucs-demo-secret';
var DEFAULT_EMAIL = 'yt.agafari@unifiedcloudsensors.com';
var MAX_PDF_ATTACHMENTS = 5;

// ─── Webhook ─────────────────────────────────────────────────────────────────

/** Browser / RAYNET health check — open deployed URL with ?secret=ucs-demo-secret */
function doGet(e) {
  e = e || {};
  if (String(e.parameter && e.parameter.secret || '') !== getSecret_()) {
    return text_('UNAUTHORIZED — add ?secret=ucs-demo-secret to the URL');
  }
  return text_('OK — webhook + Gemini agent ready. Edit RAYNET meeting → Save → Gmail Drafts with PDFs.');
}

function doPost(e) {
  e = e || {};
  var out = { status: 'error', fields: {}, draft_created: false };
  try {
    var body = getBody_(e);
    saveLastBody_(body, e);
    if (!checkSecret_(e, body)) {
      out.error = 'UNAUTHORIZED — add ?secret=ucs-demo-secret to RAYNET webhook URL '
        + 'AND webhook_secret=ucs-demo-secret in webhook body. '
        + 'Script expects: ' + getSecret_()
        + ' | Run inspectLastWebhook() to see what RAYNET sent.';
      logRow_('UNAUTHORIZED', {}, out);
      return json_(out);
    }

    var raw = parseJson_(body, e);
    raw = coalesce_(raw);
    raw = loadMeetingData_(raw);

    var f = mapFields_(raw);
    var draft = createDraft_(f, raw);
    out.fields = f;
    out.draft_created = draft.ok;
    out.draft_id = draft.draftId || '';
    out.draft_error = draft.error || '';
    out.doc_ids = draft.docIds || [];
    out.retrieval = draft.retrieval || '';
    out.status = fieldsEmpty_(f) ? 'no_fields' : 'ok';
    if (fieldsEmpty_(f)) out.error = emptyDraftHelp_(raw);

    logRow_(out.status === 'ok' ? 'OK' : 'EMPTY', f, out);
    return json_(out);
  } catch (err) {
    out.error = String(err);
    logRow_('ERROR', out.fields || {}, out);
    return json_(out);
  }
}

/** After saving a RAYNET meeting — check last log + Gmail Drafts. */
function lastMeeting() {
  var sh = getLogSheet_();
  if (!sh || sh.getLastRow() < 2) {
    Logger.log('Nothing logged yet — webhook may not be reaching Apps Script.');
    return null;
  }
  var r = sh.getRange(sh.getLastRow(), 1, sh.getLastRow(), 10).getValues()[0];
  Logger.log([
    'Status:    ' + r[1],
    'Company:   ' + r[2],
    'Subject:   ' + r[3],
    'Date:      ' + r[4],
    'Questions: ' + String(r[5]).substring(0, 120),
    'Source:    ' + r[7],
    'Draft:     ' + r[8],
    'Error:     ' + r[9],
  ].join('\n'));
  return r;
}

/** Run once from UCS-Knowledge-Base sheet — saves sheet ID for webhook logging. */
function saveSpreadsheetId_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) throw new Error('Open UCS-Knowledge-Base sheet first.');
  PropertiesService.getScriptProperties().setProperty('SPREADSHEET_ID', ss.getId());
  Logger.log('Saved SPREADSHEET_ID: ' + ss.getId());
  return ss.getId();
}

/** Checklist — run in Apps Script, read Execution log. */
function showSetupStatus() {
  var p = PropertiesService.getScriptProperties();
  var lines = [
    '=== RAYNET meeting draft setup ===',
    'WEBHOOK_SECRET: ' + (p.getProperty('WEBHOOK_SECRET') ? 'set' : 'default ucs-demo-secret'),
    'DRAFT_EMAIL: ' + (p.getProperty('DRAFT_EMAIL') || DEFAULT_EMAIL),
    'RAYNET_USER: ' + (p.getProperty('RAYNET_USER') ? 'set' : 'MISSING'),
    'RAYNET_API_KEY: ' + (p.getProperty('RAYNET_API_KEY') ? 'set' : 'MISSING'),
    'RAYNET_INSTANCE: ' + (p.getProperty('RAYNET_INSTANCE') || p.getProperty('RAYNET_INSTANCE_ID') || 'MISSING'),
    'GEMINI_API_KEY: ' + (p.getProperty('GEMINI_API_KEY') ? 'set' : 'MISSING'),
    'USE_GEMINI: ' + (useGemini_() ? 'true' : 'false'),
    'SPREADSHEET_ID: ' + (p.getProperty('SPREADSHEET_ID') || 'not set — run saveSpreadsheetId_()'),
  ];
  try {
    getLogSheet_();
    lines.push('Webhook-Log sheet: OK');
  } catch (e) {
    lines.push('Webhook-Log sheet: FAIL — ' + e);
  }
  if (hasApi_()) {
    var api = fetchLatestMeeting_();
    lines.push('RAYNET API: ' + (api.ok ? 'OK — latest meeting id ' + meetingId_(api.data) : 'FAIL — ' + api.error));
  } else {
    lines.push('RAYNET API: not configured');
  }
  lines.push('');
  lines.push('Gmail drafts go to the account that deployed the web app (Execute as Me).');
  lines.push('Check Gmail → Drafts (not Inbox).');
  Logger.log(lines.join('\n'));
  return lines.join('\n');
}

/** Test API without webhook — creates a draft from latest RAYNET meeting. */
function pullDraftFromRaynet() {
  if (!hasApi_()) throw new Error('Set RAYNET_USER, RAYNET_API_KEY, RAYNET_INSTANCE=ucs');
  var latest = fetchLatestMeeting_();
  if (!latest.ok) throw new Error(latest.error || 'API failed');
  var raw = mergeApi_(latest.data, 'raynet_api_latest');
  var f = mapFields_(raw);
  var draft = createDraft_(f, raw);
  logRow_(draft.ok ? 'OK' : 'ERROR', f, { draft_created: draft.ok, error: draft.error });
  Logger.log('Draft: ' + (draft.ok ? 'YES — open Gmail Drafts' : 'NO — ' + draft.error));
  Logger.log('Company: ' + f.company + ' | Subject: ' + f.subject);
  return { fields: f, draft: draft };
}

/** Simulates RAYNET automation webhook — uses Subject + Account to fetch full meeting from API. */
function testWebhookLocally() {
  var body = JSON.stringify({
    webhook_secret: getSecret_(),
    company: 'AgriScale Task trail',
    discussion_topics: 'AGRI-LIVE-77',
    description: 'Test from Apps Script',
    meeting_date: '2026-07-13 09:00',
  });
  var out = doPost({
    postData: { contents: body, type: 'application/json' },
    parameter: { secret: getSecret_() },
  });
  Logger.log(out.getContent());
  lastMeeting();
}

/** Simulates OpenAPI record.updated webhook (entityId only — needs RAYNET API). */
function testRecordUpdatedWebhook() {
  var body = JSON.stringify({
    type: 'record.updated',
    eventId: 'test-' + new Date().getTime(),
    author: 'test@unifiedcloudsensors.com',
    data: { entityName: 'Meeting', entityId: 5991 },
  });
  var out = doPost({
    postData: { contents: body, type: 'application/json' },
    parameter: { secret: getSecret_() },
  });
  Logger.log(out.getContent());
  lastMeeting();
}

// ─── Load meeting: webhook → API by id → API latest ──────────────────────────

// On every Save: load FULL meeting from RAYNET API (webhook alone is often empty).
function loadMeetingData_(raw) {
  raw = coalesce_(raw);
  if (!hasApi_()) {
    raw._hint = 'Set RAYNET_USER, RAYNET_API_KEY, RAYNET_INSTANCE=ucs — required for full draft on each save';
    return raw;
  }
  var loaded = fetchMeetingForWebhook_(raw);
  return loaded || raw;
}

function mergeApi_(d, source, matchNote) {
  d = d || {};
  var raw = Object.assign({}, d);
  raw._field_source = source;
  if (matchNote) raw._match_note = matchNote;
  return raw;
}

// ─── All RAYNET calendar fields → draft (edit labels/keys here) ─────────────

var MEETING_DRAFT_ROWS = [
  ['Activity type', 'activity_type'],
  ['Subject', 'subject'],
  ['Status', 'status'],
  ['Completed', 'completed'],
  ['Scheduled from', 'scheduled_from'],
  ['Scheduled to', 'scheduled_to'],
  ['Duration', 'duration'],
  ['Account', 'company'],
  ['Contact', 'contact'],
  ['Owner', 'owner'],
  ['Participants', 'participants'],
  ['Location', 'location'],
  ['Priority', 'priority'],
  ['Category', 'category'],
  ['Tags', 'tags'],
  ['Questions to Discuss', 'questions'],
  ['Meeting outcome', 'outcome'],
  ['Deal / Business case', 'business_case'],
  ['Attachments', 'attachments'],
  ['Meeting ID', 'meeting_id'],
  ['Data source', 'source'],
  ['Match note', 'match_note'],
];

function mapFields_(raw) {
  raw = raw || {};
  return {
    activity_type: isWorkflowPing_(raw) ? 'MEETING' : String(first_(raw.type, raw.activityType) || 'MEETING').toUpperCase(),
    subject: stripHtml_(first_(raw.title, raw.discussion_topics, raw.Subject)),
    status: enumLabel_(raw.status),
    completed: parseDateTime_(raw.completed),
    scheduled_from: parseDateTime_(first_(raw.scheduledFrom, raw.meeting_date)),
    scheduled_to: parseDateTime_(raw.scheduledTill),
    duration: calcDuration_(raw.scheduledFrom, raw.scheduledTill),
    company: companyName_(raw.company || raw.Account || raw.account),
    contact: personDetail_(raw.person || raw.contact),
    owner: personDetail_(raw.owner),
    participants: formatParticipants_(raw.participants || raw.participant),
    location: formatLocation_(raw.location),
    priority: enumLabel_(raw.priority),
    category: enumLabel_(raw.category),
    tags: formatTags_(raw.tags),
    questions: stripHtml_(first_(raw.description, raw.notes, raw.meeting_report)),
    outcome: stripHtml_(first_(raw.solution, raw.meeting_outcome)),
    business_case: companyName_(raw.businessCase || raw.deal),
    attachments: String(raw.attachmentCount != null ? raw.attachmentCount : (raw.attachments || '0')),
    meeting_id: meetingId_(raw),
    source: raw._field_source || 'webhook',
    match_note: String(raw._match_note || raw._api_error || '').trim(),
  };
}

function fieldsEmpty_(f) {
  f = f || {};
  return !f.company && !f.subject && !f.questions && !f.scheduled_from && !f.meeting_id;
}

// ─── Gmail draft — every field on its own line ───────────────────────────────

function createDraft_(f, raw) {
  var to = PropertiesService.getScriptProperties().getProperty('DRAFT_EMAIL') || DEFAULT_EMAIL;

  if (useGemini_()) {
    var agent = runGeminiAgent_(f);
    if (agent.ok) {
      try {
        var attachResult = getDriveBlobsForDocs_(agent.docIds);
        var blobs = attachResult.blobs;
        var attachNote = buildAttachedFilesNote_(attachResult);
        var opts = {
          htmlBody: agent.html + attachNote.html,
          attachments: blobs,
        };
        var d = GmailApp.createDraft(
          to,
          agent.subject,
          agent.plain + attachNote.plain,
          opts
        );
        return {
          ok: true, draftId: d.getId(), error: attachResult.errors.join('; '),
          docIds: agent.docIds, retrieval: agent.retrieval,
          attachment_count: blobs.length,
          attachment_names: attachResult.names,
        };
      } catch (e) {
        return { ok: false, draftId: '', error: String(e), docIds: agent.docIds, retrieval: agent.retrieval };
      }
    }
  }

  var email = buildDraftBody_(f, raw);
  try {
    var d2 = GmailApp.createDraft(to, email.subject, email.plain, { htmlBody: email.html });
    return { ok: true, draftId: d2.getId(), error: '', docIds: [], retrieval: 'fields_only' };
  } catch (e) {
    return { ok: false, draftId: '', error: String(e), docIds: [], retrieval: '' };
  }
}

function buildDraftBody_(f, raw) {
  f = f || {};
  raw = raw || {};
  var rows = MEETING_DRAFT_ROWS;

  var plain = ['Hi,', '', 'RAYNET calendar meeting — all fields:', ''];
  var html = '<p>Hi,</p><p><strong>RAYNET calendar meeting — all fields:</strong></p>'
    + '<table border="1" cellpadding="6" style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px;">';

  rows.forEach(function (row) {
    var label = row[0];
    var key = row[1];
    var val = String(f[key] || '').trim() || '—';
    plain.push(label + ': ' + val);
    html += '<tr><td style="vertical-align:top;width:200px;"><strong>' + esc_(label)
      + '</strong></td><td>' + esc_(val).replace(/\n/g, '<br>') + '</td></tr>';
  });

  if (fieldsEmpty_(f)) {
    var fix = emptyDraftHelp_(raw);
    plain.push('', fix);
    html += '<tr><td colspan="2" style="color:#b00;white-space:pre-wrap;">' + esc_(fix) + '</td></tr>';
  }

  plain.push('', 'Best regards,', 'UCS Sales');
  html += '</table><p>Best regards,<br>UCS Sales</p>';

  var subj = 'RAYNET Meeting';
  if (f.company) subj += ' — ' + f.company;
  else if (f.subject) subj += ' — ' + f.subject;

  return { subject: subj, plain: plain.join('\n'), html: html };
}

// ─── Gemini agent + knowledge base + PDF attachments ─────────────────────────

function useGemini_() {
  var p = PropertiesService.getScriptProperties();
  return p.getProperty('GEMINI_API_KEY') &&
    String(p.getProperty('USE_GEMINI') || 'true').toLowerCase() === 'true';
}

function setupOnce() {
  saveSpreadsheetId_();
  var ss = getSpreadsheet_();
  var tabs = ss.getSheets().map(function (s) { return s.getName(); });
  Logger.log('Spreadsheet: ' + ss.getName());
  Logger.log('Tabs: ' + tabs.join(', '));
  if (tabs.indexOf(DOC_SHEET) < 0) Logger.log('MISSING: import Document-Index.csv → tab "' + DOC_SHEET + '"');
  if (tabs.indexOf(LINKS_SHEET) < 0) Logger.log('MISSING: import Drive-Links.csv → tab "' + LINKS_SHEET + '"');
  if (!useGemini_()) Logger.log('MISSING: GEMINI_API_KEY in Script properties');
  else Logger.log('Gemini: OK');
  Logger.log('Run testGemini() next.');
}

function testGemini() {
  var f = {
    company: 'AgriScale GmbH',
    subject: 'SensSILO silo monitoring pricing SaaS',
    scheduled_from: '13.7.2026 09:00',
    questions: '38 grain silos, remote monitoring, SaaS subscription pricing',
    outcome: 'Send SensWEIGHT silo leaflet and SaaS pricing. Follow up next week.',
    owner: 'Jan Novak',
  };
  var agent = runGeminiAgent_(f);
  Logger.log(JSON.stringify(agent, null, 2));
  if (agent.ok) {
    var draft = createDraft_(f, {});
    Logger.log('Draft created: ' + draft.ok + ' | PDFs attached: ' + (draft.attachment_count || 0));
    Logger.log('Check Gmail → Drafts');
  }
  return agent;
}

function runGeminiAgent_(f) {
  f = f || {};
  try {
    var catalog = loadDocumentCatalog_();
    if (!catalog.length) {
      return { ok: false, error: 'Document-Index tab empty or missing — import knowledge-base/sheets/Document-Index.csv' };
    }
    var keywordHits = keywordSearchDocs_(f, catalog, 12);
    var gemini = callGeminiForFollowUp_(f, catalog, keywordHits);
    if (gemini.ok) return gemini;
    return buildKeywordFallbackEmail_(f, keywordHits);
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

function loadDocumentCatalog_() {
  var sh = getSpreadsheet_().getSheetByName(DOC_SHEET);
  if (!sh || sh.getLastRow() < 2) return [];
  var rows = sh.getDataRange().getValues();
  var header = rows[0].map(function (h) { return String(h || '').trim().toLowerCase(); });
  var idx = {
    doc_id: header.indexOf('doc_id'),
    title: header.indexOf('title'),
    doc_type: header.indexOf('doc_type'),
    keywords: header.indexOf('keywords'),
    drive_path: header.indexOf('drive_path'),
  };
  var out = [];
  for (var r = 1; r < rows.length; r++) {
    var row = rows[r];
    var docId = String(row[idx.doc_id] || '').trim();
    if (!docId) continue;
    out.push({
      doc_id: docId,
      title: String(row[idx.title] || '').trim(),
      doc_type: String(row[idx.doc_type] || '').trim(),
      keywords: String(row[idx.keywords] || '').trim(),
      drive_path: idx.drive_path >= 0 ? String(row[idx.drive_path] || '').trim() : '',
    });
  }
  return out;
}

function loadDriveLinksMap_() {
  var sh = getSpreadsheet_().getSheetByName(LINKS_SHEET);
  if (!sh || sh.getLastRow() < 2) return {};
  var rows = sh.getDataRange().getValues();
  var map = {};
  for (var r = 1; r < rows.length; r++) {
    var docId = String(rows[r][0] || '').trim();
    var fileId = normalizeDriveFileId_(rows[r][1]);
    if (docId && fileId) map[docId] = fileId;
  }
  return map;
}

function meetingSearchText_(f) {
  f = f || {};
  return [
    f.company, f.subject, f.questions, f.outcome, f.tags, f.business_case,
  ].filter(Boolean).join(' ').toLowerCase();
}

function keywordSearchDocs_(f, catalog, limit) {
  limit = limit || 8;
  var text = meetingSearchText_(f);
  var tokens = tokenize_(text);
  var scored = catalog.map(function (doc) {
    var kw = String(doc.keywords + ' ' + doc.title + ' ' + doc.doc_type).toLowerCase();
    var score = 0;
    tokens.forEach(function (t) {
      if (t.length < 3) return;
      if (kw.indexOf(t) >= 0) score += t.length > 5 ? 3 : 2;
    });
    if (text.indexOf(doc.doc_id.toLowerCase()) >= 0) score += 5;
    return { doc: doc, score: score };
  });
  scored.sort(function (a, b) { return b.score - a.score; });
  return scored.filter(function (s) { return s.score > 0; }).slice(0, limit).map(function (s) { return s.doc; });
}

function tokenize_(text) {
  return String(text || '').toLowerCase().replace(/[^a-z0-9\s-]/g, ' ')
    .split(/\s+/).filter(function (w) { return w.length >= 2; });
}

function callGeminiForFollowUp_(f, catalog, keywordHits) {
  var key = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!key) return { ok: false, error: 'GEMINI_API_KEY not set' };

  var catalogLines = catalog.map(function (d) {
    return d.doc_id + ' | ' + d.doc_type + ' | ' + d.title + ' | ' + d.keywords.substring(0, 120);
  }).join('\n');

  var hintIds = keywordHits.map(function (d) { return d.doc_id; }).join(', ');

  var prompt =
    'You are a UCS (Unified Cloud Sensors) sales assistant.\n'
    + 'Write a professional follow-up email draft for the customer after a CRM meeting.\n'
    + 'Select 1-' + MAX_PDF_ATTACHMENTS + ' document IDs from the catalog to attach as PDFs.\n'
    + 'Prefer: marketing leaflet + pricing and/or datasheet + certification when relevant.\n'
    + 'Only use doc_id values that exist in the catalog.\n'
    + 'Do NOT include Google Drive URLs or links in the email — PDF files are attached automatically.\n\n'
    + 'MEETING:\n'
    + '- Company: ' + (f.company || '') + '\n'
    + '- Subject: ' + (f.subject || '') + '\n'
    + '- Date: ' + (f.scheduled_from || '') + '\n'
    + '- Questions discussed: ' + (f.questions || '') + '\n'
    + '- Meeting outcome / notes: ' + (f.outcome || '') + '\n'
    + '- Owner: ' + (f.owner || '') + '\n\n'
    + 'Keyword search suggests: ' + (hintIds || 'none') + '\n\n'
    + 'DOCUMENT CATALOG (doc_id | type | title | keywords):\n' + catalogLines + '\n\n'
    + 'Respond with JSON only:\n'
    + '{\n'
    + '  "doc_ids": ["MKT-SW-SILO"],\n'
    + '  "email_subject": "Follow-up: ...",\n'
    + '  "email_plain": "plain text email body with greeting and sign-off UCS Sales",\n'
    + '  "email_html": "<p>html version</p>"\n'
    + '}';

  var model = PropertiesService.getScriptProperties().getProperty('GEMINI_MODEL') || 'gemini-2.0-flash';
  var url = 'https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent?key=' + key;
  var res = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.35, responseMimeType: 'application/json' },
    }),
    muteHttpExceptions: true,
  });

  if (res.getResponseCode() !== 200) {
    return { ok: false, error: 'Gemini HTTP ' + res.getResponseCode() + ': ' + res.getContentText().substring(0, 300) };
  }

  var body = JSON.parse(res.getContentText());
  var text = body.candidates && body.candidates[0] && body.candidates[0].content
    && body.candidates[0].content.parts && body.candidates[0].content.parts[0]
    ? body.candidates[0].content.parts[0].text : '';
  var parsed = parseGeminiJson_(text);
  if (!parsed.email_plain) return { ok: false, error: 'Gemini returned empty email' };

  var validIds = filterValidDocIds_(parsed.doc_ids || [], catalog);
  if (!validIds.length && keywordHits.length) {
    validIds = keywordHits.slice(0, 3).map(function (d) { return d.doc_id; });
  }

  return {
    ok: true,
    subject: parsed.email_subject || ('Follow-up: ' + (f.company || f.subject || 'UCS meeting')),
    plain: parsed.email_plain,
    html: parsed.email_html || esc_(parsed.email_plain).replace(/\n/g, '<br>'),
    docIds: validIds,
    retrieval: 'gemini',
  };
}

function parseGeminiJson_(text) {
  text = String(text || '').trim();
  if (text.indexOf('```') >= 0) {
    text = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  }
  return JSON.parse(text);
}

function filterValidDocIds_(ids, catalog) {
  var valid = {};
  catalog.forEach(function (d) { valid[d.doc_id] = true; });
  var out = [];
  (ids || []).forEach(function (id) {
    id = String(id || '').trim();
    if (id && valid[id] && out.indexOf(id) < 0) out.push(id);
  });
  return out.slice(0, MAX_PDF_ATTACHMENTS);
}

function buildKeywordFallbackEmail_(f, keywordHits) {
  var docIds = keywordHits.slice(0, 3).map(function (d) { return d.doc_id; });
  var docList = keywordHits.slice(0, 5).map(function (d) {
    return '- ' + d.doc_id + ': ' + d.title + ' (' + d.doc_type + ')';
  }).join('\n');
  var plain =
    'Hi,\n\n'
    + 'Thank you for meeting with us regarding ' + (f.subject || 'your project') + '.\n\n'
    + 'Based on our discussion with ' + (f.company || 'your company') + ':\n'
    + (f.questions || '(see meeting notes)') + '\n\n'
    + 'Recommended documents:\n' + (docList || '(none matched — update Document-Index keywords)') + '\n\n'
    + 'Next steps:\n' + (f.outcome || 'We will follow up shortly.') + '\n\n'
    + 'Best regards,\nUCS Sales';
  return {
    ok: true,
    subject: 'Follow-up: ' + (f.company || f.subject || 'UCS meeting'),
    plain: plain,
    html: '<p>' + esc_(plain).replace(/\n/g, '<br>') + '</p>',
    docIds: docIds,
    retrieval: 'keywords',
  };
}

/** Lists attached filenames in the email body — no Drive URLs. */
function buildAttachedFilesNote_(attachResult) {
  attachResult = attachResult || { blobs: [], names: [], errors: [] };
  var names = attachResult.names || [];
  if (!names.length) {
    var err = (attachResult.errors || []).join('; ');
    var plain = '\n\n(PDF attachments could not be loaded'
      + (err ? ': ' + err : ' — check Drive-Links sheet and Drive sharing') + ')';
    return { plain: plain, html: '<p style="color:#b00;">' + esc_(plain) + '</p>' };
  }
  var plain = '\n\nAttached documents:\n';
  var html = '<p><strong>Attached documents:</strong></p><ul>';
  names.forEach(function (name) {
    plain += '- ' + name + '\n';
    html += '<li>' + esc_(name) + '</li>';
  });
  html += '</ul>';
  return { plain: plain, html: html };
}

function normalizeDriveFileId_(value) {
  value = String(value || '').trim();
  if (!value) return '';
  var m = value.match(/\/folders\/([a-zA-Z0-9_-]+)/);
  if (m) return m[1];
  m = value.match(/\/d\/([a-zA-Z0-9_-]+)/);
  if (m) return m[1];
  m = value.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  if (m) return m[1];
  return value.replace(/\s/g, '');
}

/** Shared Drive + My Drive — required query flags for Google Drive API v3. */
function driveApiFetch_(url, options) {
  options = options || {};
  var token = ScriptApp.getOAuthToken();
  var headers = options.headers || {};
  headers.Authorization = 'Bearer ' + token;
  return UrlFetchApp.fetch(url, {
    method: options.method || 'get',
    headers: headers,
    muteHttpExceptions: true,
  });
}

function withSharedDriveParams_(url) {
  var sep = url.indexOf('?') >= 0 ? '&' : '?';
  return url + sep + 'supportsAllDrives=true';
}

function getDriveFileName_(fileId) {
  var probe = probeDriveFile_(fileId);
  return probe.ok ? probe.name : '';
}

/** Returns HTTP status + hint — works for My Drive and Shared Drives. */
function probeDriveFile_(fileId) {
  fileId = normalizeDriveFileId_(fileId);
  var email = '';
  try { email = Session.getActiveUser().getEmail(); } catch (ignore) {}
  if (!fileId) {
    return { ok: false, code: 0, hint: 'Empty file ID in Drive-Links column B' };
  }
  try {
    var url = withSharedDriveParams_(
      'https://www.googleapis.com/drive/v3/files/' + fileId + '?fields=name,mimeType,driveId'
    );
    var meta = driveApiFetch_(url);
    var code = meta.getResponseCode();
    if (code === 200) {
      var info = JSON.parse(meta.getContentText());
      return {
        ok: true, code: 200, name: info.name, mimeType: info.mimeType,
        fileId: fileId, sharedDrive: !!info.driveId,
      };
    }
    if (code === 404) {
      return {
        ok: false, code: 404, fileId: fileId,
        hint: 'File not found — wrong ID, or file moved. '
          + 'Open PDF in browser, copy new ID from URL, run syncDriveLinksFromFolder().',
      };
    }
    if (code === 403) {
      return {
        ok: false, code: 403, fileId: fileId,
        hint: 'No access to Shared Drive file — ask admin to add ' + (email || 'deploy account')
          + ' as Content manager or Contributor on the shared drive/folder.',
      };
    }
    return { ok: false, code: code, fileId: fileId, hint: 'Drive API HTTP ' + code + ': ' + meta.getContentText().substring(0, 120) };
  } catch (e) {
    return { ok: false, code: 0, hint: String(e) };
  }
}

function downloadPdfBlobFromDrive_(fileId, fallbackName) {
  fileId = normalizeDriveFileId_(fileId);
  if (!fileId) return null;

  var probe = probeDriveFile_(fileId);
  if (!probe.ok) return null;

  var url = withSharedDriveParams_(
    'https://www.googleapis.com/drive/v3/files/' + fileId + '?alt=media'
  );
  var res = driveApiFetch_(url);
  if (res.getResponseCode() === 200) {
    var name = probe.name || fallbackName || (fileId + '.pdf');
    if (name.toLowerCase().indexOf('.pdf') < 0) name += '.pdf';
    return Utilities.newBlob(res.getBytes(), 'application/pdf', name);
  }

  try {
    var file = DriveApp.getFileById(fileId);
    var blob = file.getBlob();
    var fname = file.getName();
    if (fname.toLowerCase().indexOf('.pdf') < 0) fname += '.pdf';
    return blob.setContentType('application/pdf').setName(fname);
  } catch (e) {
    return null;
  }
}

function getDriveBlobsForDocs_(docIds) {
  var links = loadDriveLinksMap_();
  var catalog = loadDocumentCatalog_();
  var titleById = {};
  catalog.forEach(function (d) { titleById[d.doc_id] = d.title; });

  var blobs = [];
  var names = [];
  var errors = [];

  (docIds || []).forEach(function (id) {
    if (blobs.length >= MAX_PDF_ATTACHMENTS) return;
    id = String(id || '').trim();
    var fileId = normalizeDriveFileId_(links[id]);
    if (!fileId) {
      errors.push(id + ': missing Drive file ID in Drive-Links column B');
      return;
    }
    var fallbackName = (titleById[id] || id).replace(/[^\w\s.-]/g, '_') + '.pdf';
    var blob = downloadPdfBlobFromDrive_(fileId, fallbackName);
    if (blob) {
      blobs.push(blob);
      names.push(blob.getName());
    } else {
      var probe = probeDriveFile_(fileId);
      var hint = probe.hint || ('could not download ' + fileId);
      if (probe.code === 403) {
        hint += ' — OLD Shared Drive ID in Drive-Links! Run fixMyDrivePdfLinks() after uploading PDFs to My Drive.';
      }
      errors.push(id + ': ' + hint);
    }
  });

  return { blobs: blobs, names: names, errors: errors };
}

function basenameFromPath_(path) {
  path = String(path || '').replace(/\\/g, '/');
  var parts = path.split('/');
  return parts[parts.length - 1] || '';
}

function findKnowledgeFolderId_() {
  var propId = PropertiesService.getScriptProperties().getProperty('KNOWLEDGE_DRIVE_FOLDER_ID');
  if (propId) return normalizeDriveFileId_(propId);

  var folders = searchDriveFoldersByName_('UCS-Knowledge-Base');
  if (!folders.length) {
    throw new Error(
      'Folder "UCS-Knowledge-Base" not found automatically. '
      + 'Shared Drive search is often blocked (HTTP 403). '
      + 'Open the shared folder in Drive → copy URL → set Script property KNOWLEDGE_DRIVE_FOLDER_ID → run checkSharedFolderAccess().'
    );
  }
  if (folders.length > 1) {
    Logger.log('Multiple UCS-Knowledge-Base folders — using first. Set KNOWLEDGE_DRIVE_FOLDER_ID to pick one:');
    folders.forEach(function (f) {
      Logger.log('  ' + f.name + ' | id=' + f.id + (f.driveId ? ' | sharedDrive=' + f.driveId : ' | My Drive'));
    });
  }
  return folders[0].id;
}

/** Search folders — My Drive first; Shared Drive search may return 403 (Workspace policy). */
function searchDriveFoldersByName_(name) {
  name = String(name || '').replace(/'/g, "\\'");
  var q = encodeURIComponent(
    "name='" + name + "' and mimeType='application/vnd.google-apps.folder' and trashed=false"
  );
  var found = {};
  var list = [];

  function addFiles(files) {
    (files || []).forEach(function (f) {
      if (!found[f.id]) {
        found[f.id] = true;
        list.push(f);
      }
    });
  }

  // 1) My Drive via DriveApp (no Shared Drive API needed)
  try {
    var it = DriveApp.getFoldersByName(name);
    while (it.hasNext()) {
      var f = it.next();
      addFiles([{ id: f.getId(), name: f.getName(), driveId: null }]);
    }
  } catch (e) {
    Logger.log('DriveApp folder search: ' + e);
  }

  // 2) My Drive via API
  var urlUser = 'https://www.googleapis.com/drive/v3/files?q=' + q
    + '&fields=files(id,name,driveId)&corpora=user&pageSize=50';
  urlUser = withSharedDriveParams_(urlUser);
  var resUser = driveApiFetch_(urlUser);
  if (resUser.getResponseCode() === 200) {
    addFiles(JSON.parse(resUser.getContentText()).files);
  } else {
    Logger.log('My Drive search HTTP ' + resUser.getResponseCode());
  }

  // 3) All Shared Drives — often blocked HTTP 403 by Workspace admin policy
  var urlAll = 'https://www.googleapis.com/drive/v3/files?q=' + q
    + '&fields=files(id,name,driveId)'
    + '&supportsAllDrives=true&includeItemsFromAllDrives=true&corpora=allDrives&pageSize=50';
  var resAll = driveApiFetch_(urlAll);
  if (resAll.getResponseCode() === 200) {
    addFiles(JSON.parse(resAll.getContentText()).files);
  } else if (resAll.getResponseCode() === 403) {
    Logger.log('Shared Drive search blocked (HTTP 403) — normal on some Workspace accounts.');
    Logger.log('Use manual setup: set KNOWLEDGE_DRIVE_FOLDER_ID to the shared folder ID from the browser URL.');
  } else {
    Logger.log('Shared Drive search HTTP ' + resAll.getResponseCode() + ': ' + resAll.getContentText().substring(0, 200));
  }

  return list;
}

/** List PDFs inside a folder by ID — works for Shared Drive when you know the folder ID. */
function collectPdfFilesInFolderApi_(folderId, out) {
  out = out || {};
  folderId = normalizeDriveFileId_(folderId);
  var pageToken = '';
  do {
    var q = encodeURIComponent("'" + folderId + "' in parents and trashed=false");
    var url = 'https://www.googleapis.com/drive/v3/files?q=' + q
      + '&fields=nextPageToken,files(id,name,mimeType)'
      + '&supportsAllDrives=true&includeItemsFromAllDrives=true&pageSize=200';
    if (pageToken) url += '&pageToken=' + pageToken;
    var res = driveApiFetch_(url);
    if (res.getResponseCode() !== 200) {
      Logger.log('List folder ' + folderId + ' failed HTTP ' + res.getResponseCode()
        + ': ' + res.getContentText().substring(0, 200));
      break;
    }
    var data = JSON.parse(res.getContentText());
    (data.files || []).forEach(function (f) {
      if (f.mimeType === 'application/vnd.google-apps.folder') {
        collectPdfFilesInFolderApi_(f.id, out);
      } else if (String(f.name).toLowerCase().indexOf('.pdf') >= 0) {
        out[f.name] = f.id;
      }
    });
    pageToken = data.nextPageToken || '';
  } while (pageToken);
  return out;
}

/**
 * STEP 1 for Shared Drive — paste folder URL here, run once, then syncDriveLinksFromFolder().
 * Example URL: https://drive.google.com/drive/folders/0AJxxxxxxxxxxxx
 */
function registerSharedKnowledgeFolder() {
  var url = 'PASTE_YOUR_SHARED_FOLDER_URL_HERE';
  var folderId = normalizeDriveFileId_(url);
  if (!folderId || url.indexOf('PASTE_') >= 0) {
    throw new Error(
      'Edit registerSharedKnowledgeFolder() line: var url = "your shared folder URL";\n'
      + 'Or set Script property KNOWLEDGE_DRIVE_FOLDER_ID manually, then run checkSharedFolderAccess().'
    );
  }
  PropertiesService.getScriptProperties().setProperty('KNOWLEDGE_DRIVE_FOLDER_ID', folderId);
  return checkSharedFolderAccess();
}

/** Validates KNOWLEDGE_DRIVE_FOLDER_ID — run after pasting shared folder ID. */
function checkSharedFolderAccess() {
  var email = '';
  try { email = Session.getActiveUser().getEmail(); } catch (ignore) {}
  var folderId = PropertiesService.getScriptProperties().getProperty('KNOWLEDGE_DRIVE_FOLDER_ID');
  if (!folderId) {
    Logger.log('MISSING: Script property KNOWLEDGE_DRIVE_FOLDER_ID');
    Logger.log('Open shared folder in Drive → copy URL → paste folder ID into Script properties');
    return { ok: false };
  }
  folderId = normalizeDriveFileId_(folderId);
  Logger.log('Account: ' + (email || 'unknown'));
  Logger.log('Folder ID: ' + folderId);

  var probe = probeDriveFile_(folderId);
  Logger.log('Folder access: ' + JSON.stringify(probe));
  if (!probe.ok) {
    Logger.log('FIX: ask admin to add ' + (email || 'you') + ' as Contributor on the Shared Drive');
    return { ok: false, probe: probe };
  }

  var pdfs = collectPdfFilesInFolderApi_(folderId);
  var names = Object.keys(pdfs);
  Logger.log('PDFs found in folder: ' + names.length);
  names.slice(0, 10).forEach(function (n) { Logger.log('  ' + n); });
  if (names.length > 10) Logger.log('  ... and ' + (names.length - 10) + ' more');
  Logger.log('Next: run syncDriveLinksFromFolder() then testPdfAttachments()');
  return { ok: true, pdfCount: names.length, probe: probe };
}

/** Lists UCS-Knowledge-Base folders (My Drive; Shared Drive search may be blocked). */
function findAllKnowledgeFolders() {
  Logger.log('Searching folders named UCS-Knowledge-Base...');
  var folders = searchDriveFoldersByName_('UCS-Knowledge-Base');
  if (!folders.length) {
    Logger.log('No folder found via search.');
    Logger.log('');
    Logger.log('MANUAL FIX (Shared Drive):');
    Logger.log('1. Open shared folder UCS-Knowledge-Base in Google Drive');
    Logger.log('2. Copy URL: https://drive.google.com/drive/folders/FOLDER_ID_HERE');
    Logger.log('3. Apps Script → Project settings → Script properties');
    Logger.log('   KNOWLEDGE_DRIVE_FOLDER_ID = FOLDER_ID_HERE');
    Logger.log('4. Run checkSharedFolderAccess()');
    return [];
  }
  folders.forEach(function (f, i) {
    Logger.log((i + 1) + '. ' + f.name + ' | id=' + f.id + (f.driveId ? ' | SHARED DRIVE' : ' | My Drive'));
  });
  Logger.log('Set KNOWLEDGE_DRIVE_FOLDER_ID to the shared folder id, then run checkSharedFolderAccess()');
  return folders;
}

/**
 * Upload PDFs to Drive folder "UCS-Knowledge-Base", then run this once.
 * Matches PDF filenames to Document-Index drive_path and fills Drive-Links column B.
 */
function syncDriveLinksFromFolder() {
  saveSpreadsheetId_();
  var folderId = findKnowledgeFolderId_();
  var probe = probeDriveFile_(folderId);
  Logger.log('Knowledge folder: ' + folderId + (probe.sharedDrive ? ' (Shared Drive)' : ' (My Drive)'));
  if (!probe.ok) throw new Error('Cannot access folder: ' + probe.hint);

  var pdfByName = collectPdfFilesInFolderApi_(folderId);
  var pdfKeys = Object.keys(pdfByName);
  Logger.log('PDF files found: ' + pdfKeys.length);
  if (!pdfKeys.length) {
    throw new Error('No PDFs in folder — upload knowledge-base/clients-package PDFs to the shared folder.');
  }

  var catalog = loadDocumentCatalog_();
  var sh = getSpreadsheet_().getSheetByName(LINKS_SHEET);
  if (!sh) throw new Error('Missing tab: ' + LINKS_SHEET);

  var rows = sh.getDataRange().getValues();
  var linked = 0;
  var missing = [];

  for (var r = 1; r < rows.length; r++) {
    var docId = String(rows[r][0] || '').trim();
    if (!docId) continue;
    var doc = null;
    for (var i = 0; i < catalog.length; i++) {
      if (catalog[i].doc_id === docId) { doc = catalog[i]; break; }
    }
    if (!doc || !doc.drive_path) {
      missing.push(docId + ' (no drive_path in Document-Index)');
      continue;
    }
    var want = basenameFromPath_(doc.drive_path);
    var fileId = pdfByName[want];
    if (!fileId) {
      var wantLower = want.toLowerCase();
      for (var k = 0; k < pdfKeys.length; k++) {
        if (pdfKeys[k].toLowerCase() === wantLower) {
          fileId = pdfByName[pdfKeys[k]];
          break;
        }
      }
    }
    if (fileId) {
      sh.getRange(r + 1, 2).setValue(fileId);
      linked++;
      Logger.log('OK ' + docId + ' → ' + want + ' → ' + fileId);
    } else {
      missing.push(docId + ' (upload ' + want + ')');
    }
  }

  PropertiesService.getScriptProperties().setProperty('KNOWLEDGE_DRIVE_FOLDER_ID', folderId);
  Logger.log('Linked ' + linked + ' doc_ids in Drive-Links.');
  if (missing.length) Logger.log('Missing PDFs:\n  ' + missing.join('\n  '));
  Logger.log('Next: run verifyDriveLinks() then testPdfAttachments()');
  return { linked: linked, missing: missing, folderId: folderId };
}

/**
 * FIX: Drive-Links still has old Shared Drive file IDs → clears column B and re-links from My Drive.
 * Run after uploading PDFs to My Drive folder UCS-Knowledge-Base.
 */
function fixMyDrivePdfLinks() {
  saveSpreadsheetId_();
  var folderId = PropertiesService.getScriptProperties().getProperty('KNOWLEDGE_DRIVE_FOLDER_ID');
  if (!folderId) {
    throw new Error('Set Script property KNOWLEDGE_DRIVE_FOLDER_ID to your MY DRIVE folder ID first.');
  }
  folderId = normalizeDriveFileId_(folderId);
  var probe = probeDriveFile_(folderId);
  Logger.log('=== fixMyDrivePdfLinks ===');
  Logger.log('Folder: ' + folderId);
  Logger.log('Access: ' + JSON.stringify(probe));
  if (!probe.ok) throw new Error('Cannot access My Drive folder: ' + probe.hint);

  var sh = getSpreadsheet_().getSheetByName(LINKS_SHEET);
  if (!sh) throw new Error('Missing tab: ' + LINKS_SHEET);
  var lastRow = sh.getLastRow();
  if (lastRow > 1) {
    sh.getRange(2, 2, lastRow, 2).clearContent();
    Logger.log('Cleared old file IDs in Drive-Links column B (removed Shared Drive IDs).');
  }

  var result = syncDriveLinksFromFolder();
  Logger.log('');
  Logger.log('Verify these rows (Gemini often picks them):');
  ['PL-SW-SAAS', 'DS-M740D', 'DS-M740-60T', 'MKT-SW-SILO'].forEach(function (id) {
    var links = loadDriveLinksMap_();
    var fid = links[id];
    if (!fid) Logger.log('  MISSING row ' + id + ' — upload PDF and run fixMyDrivePdfLinks() again');
    else Logger.log('  ' + id + ' → ' + (probeDriveFile_(fid).ok ? 'OK' : 'FAIL') + ' (' + fid + ')');
  });
  Logger.log('Next: testPdfAttachments() then save a RAYNET meeting');
  return result;
}

/** Check every row in Drive-Links — run after syncDriveLinksFromFolder. */
function verifyDriveLinks() {
  var email = '';
  try { email = Session.getActiveUser().getEmail(); } catch (ignore) {}
  Logger.log('Apps Script runs as: ' + (email || '(unknown)'));
  var sh = getSpreadsheet_().getSheetByName(LINKS_SHEET);
  if (!sh) throw new Error('Missing Drive-Links tab');
  var rows = sh.getDataRange().getValues();
  var ok = 0;
  var bad = 0;
  for (var r = 1; r < rows.length; r++) {
    var docId = String(rows[r][0] || '').trim();
    var fileId = normalizeDriveFileId_(rows[r][1]);
    if (!docId) continue;
    if (!fileId) {
      Logger.log('SKIP ' + docId + ': empty file ID');
      bad++;
      continue;
    }
    var probe = probeDriveFile_(fileId);
    if (probe.ok) {
      Logger.log('OK   ' + docId + ' → ' + probe.name);
      ok++;
    } else {
      Logger.log('FAIL ' + docId + ' HTTP ' + probe.code + ' — ' + probe.hint);
      bad++;
    }
  }
  Logger.log('Summary: ' + ok + ' OK, ' + bad + ' failed');
  return { ok: ok, bad: bad };
}

/** Test PDF download + draft with real attachments — run from Apps Script. */
function testPdfAttachments() {
  var email = '';
  try { email = Session.getActiveUser().getEmail(); } catch (ignore) {}
  Logger.log('Deploy account: ' + (email || 'unknown'));

  var docIds = ['MKT-SW-SILO', 'PL-SW-SAAS'];
  docIds.forEach(function (id) {
    var links = loadDriveLinksMap_();
    var fid = links[id];
    if (fid) Logger.log(id + ' fileId=' + fid + ' → ' + JSON.stringify(probeDriveFile_(fid)));
  });

  var result = getDriveBlobsForDocs_(docIds);
  Logger.log('Blobs: ' + result.blobs.length);
  Logger.log('Names: ' + result.names.join(', '));
  Logger.log('Errors: ' + (result.errors.join('; ') || 'none'));
  if (!result.blobs.length) {
    Logger.log('');
    Logger.log('FIX for Shared Drive (do in order):');
    Logger.log('1. Ask admin: add yt.agafari@... as Contributor on the shared drive');
    Logger.log('2. Open shared folder UCS-Knowledge-Base → copy URL');
    Logger.log('3. Apps Script → Project settings → Script property KNOWLEDGE_DRIVE_FOLDER_ID = folder ID from URL');
    Logger.log('   Or run findAllKnowledgeFolders() to list folder IDs');
    Logger.log('4. Run syncDriveLinksFromFolder() — updates Drive-Links with new shared file IDs');
    Logger.log('5. Run verifyDriveLinks() then testPdfAttachments()');
    return result;
  }
  var to = PropertiesService.getScriptProperties().getProperty('DRAFT_EMAIL') || DEFAULT_EMAIL;
  var note = buildAttachedFilesNote_(result);
  GmailApp.createDraft(
    to,
    'TEST — PDF attachments',
    'This draft should have PDF files attached (not links).' + note.plain,
    { htmlBody: '<p>PDF attachment test</p>' + note.html, attachments: result.blobs }
  );
  Logger.log('Draft created — open Gmail → Drafts and verify paperclip + .pdf files');
  return result;
}

// ─── RAYNET API ──────────────────────────────────────────────────────────────

function hasApi_() {
  var p = PropertiesService.getScriptProperties();
  return !!(p.getProperty('RAYNET_USER') && p.getProperty('RAYNET_API_KEY') &&
    (p.getProperty('RAYNET_INSTANCE') || p.getProperty('RAYNET_INSTANCE_ID')));
}

function fetchMeetingById_(id) {
  return apiGet_('/meeting/' + id + '/');
}

function fetchLatestMeeting_() {
  var res = apiGet_(
    '/meeting/?offset=0&limit=100&sortColumn=rowInfo.lastModifiedAt&sortDirection=DESC'
  );
  if (!res.ok) return res;
  var list = res.data;
  if (!list || !list.length) return { ok: false, error: 'No meetings in RAYNET API' };
  var latest = list[0];
  var id = meetingId_(latest);
  if (id) {
    var full = fetchMeetingById_(id);
    if (full.ok) return full;
  }
  return { ok: true, data: latest };
}

function fetchMeetingForWebhook_(raw) {
  raw = raw || {};
  var subject = String(first_(raw.discussion_topics, raw.title, raw.subject, raw.Title, raw.Subject) || '').trim();
  var company = companyName_(first_(raw.company, raw.Account, raw.account, raw.Company));
  raw._webhook_subject = subject;
  raw._webhook_company = company;

  // OpenAPI webhook: record.updated sends only entityId + entityName
  if (isRecordEvent_(raw)) {
    var entityName = String(raw.entityName || '').toLowerCase();
    var id = meetingId_(raw);
    if (id && (!entityName || entityName === 'meeting' || entityName === 'activity')) {
      var byEvent = fetchMeetingById_(id);
      if (byEvent.ok) {
        return mergeApi_(byEvent.data, 'raynet_api_record_event', 'entityId=' + id);
      }
      raw._api_error = byEvent.error;
    } else if (entityName && entityName !== 'meeting' && entityName !== 'activity') {
      raw._api_error = 'Skipped non-meeting record.updated: ' + entityName;
      raw._field_source = 'webhook';
      return raw;
    }
  }

  var id = meetingId_(raw);
  if (id) {
    var byId = fetchMeetingById_(id);
    if (byId.ok) return mergeApi_(byId.data, 'raynet_api_id', 'meeting_id=' + id);
    raw._api_error = byId.error;
  }

  var listRes = apiGet_(
    '/meeting/?offset=0&limit=100&sortColumn=rowInfo.lastModifiedAt&sortDirection=DESC'
  );
  if (!listRes.ok) {
    raw._api_error = raw._api_error || listRes.error || 'API list failed';
    return raw;
  }
  var list = listRes.data || [];
  if (!list.length) {
    raw._api_error = 'No meetings in RAYNET API';
    return raw;
  }

  // User just clicked Save — prefer meeting modified in the last 3 minutes
  var justSaved = pickJustSavedMeeting_(list, subject, company, 3);
  if (justSaved.ok) {
    return mergeApi_(justSaved.data, 'raynet_api_just_saved', justSaved.note);
  }

  if (!subject && !company) {
    raw._api_error = 'WEBHOOK_EMPTY — map discussion_topics=Subject, company=Account in RAYNET';
    raw._field_source = 'webhook';
    return raw;
  }

  if (isStaticTestText_(subject)) {
    raw._api_error = 'WEBHOOK_STATIC_TEXT — RAYNET still sends test payload ("' + subject
      + '"). Delete old webhook, create UCS-Meeting-Live (URL only), remap fields.';
    raw._field_source = 'webhook';
    return raw;
  }

  // Strict match only — never pick a random meeting on partial company name alone
  var matched = pickMeetingMatchStrict_(list, subject, company);
  if (matched) {
    var fullMatch = fetchMeetingById_(meetingId_(matched));
    if (fullMatch.ok) {
      return mergeApi_(fullMatch.data, 'raynet_api_webhook_match',
        'title="' + (matched.title || '') + '" company="' + companyName_(matched.company) + '"');
    }
    raw._api_error = fullMatch.error;
  }

  raw._api_error = 'NO_MATCH — webhook subject="' + subject + '" company="' + company
    + '". Fix RAYNET field mapping or add meeting_id to webhook body.';
  raw._field_source = 'webhook';
  return raw;
}

/** Meeting edited in the last N minutes — the one the user just saved. */
function pickJustSavedMeeting_(list, subject, company, withinMinutes) {
  withinMinutes = withinMinutes || 3;
  var cutoff = Date.now() - withinMinutes * 60 * 1000;
  var recent = [];
  list.forEach(function (m) {
    var t = parseRaynetTime_(rowModifiedAt_(m));
    if (t && t >= cutoff) recent.push(m);
  });
  if (!recent.length) return { ok: false };

  var sub = normMatch_(subject);
  var comp = normMatch_(company);

  // Best: recent meeting whose title + company match webhook
  for (var i = 0; i < recent.length; i++) {
    var m = recent[i];
    if (meetingMatchesWebhook_(m, sub, comp, true)) {
      var full = fetchMeetingById_(meetingId_(m));
      if (full.ok) {
        return {
          ok: true, data: full.data,
          note: 'just saved (3 min) + exact match title="' + (m.title || '') + '"',
        };
      }
    }
  }

  // Recent + loose match (company contains / subject contains)
  for (var j = 0; j < recent.length; j++) {
    var m2 = recent[j];
    if (meetingMatchesWebhook_(m2, sub, comp, false)) {
      var full2 = fetchMeetingById_(meetingId_(m2));
      if (full2.ok) {
        return {
          ok: true, data: full2.data,
          note: 'just saved (3 min) + partial match title="' + (m2.title || '') + '"',
        };
      }
    }
  }

  // Only one meeting edited recently — trust it (status-only save)
  if (recent.length === 1) {
    var only = fetchMeetingById_(meetingId_(recent[0]));
    if (only.ok) {
      return {
        ok: true, data: only.data,
        note: 'just saved (3 min) — only one recent edit: "' + (recent[0].title || '') + '"',
      };
    }
  }

  return { ok: false };
}

function meetingMatchesWebhook_(m, sub, comp, exact) {
  var mt = normMatch_(m.title || '');
  var mc = normMatch_(companyName_(m.company));
  if (exact) {
    var subjectOk = !sub || mt === sub;
    var companyOk = !comp || mc === comp;
    return subjectOk && companyOk;
  }
  var subjectOk2 = !sub || mt === sub || mt.indexOf(sub) >= 0 || sub.indexOf(mt) >= 0;
  var companyOk2 = !comp || mc === comp || mc.indexOf(comp) >= 0 || comp.indexOf(mc) >= 0;
  return subjectOk2 && companyOk2;
}

/** Requires exact subject (10+) or exact subject + company (18+). No weak partial-only match. */
function pickMeetingMatchStrict_(list, subject, company) {
  var sub = normMatch_(subject);
  var comp = normMatch_(company);
  var best = null;
  var bestScore = 0;

  list.forEach(function (m) {
    var mt = normMatch_(m.title || '');
    var mc = normMatch_(companyName_(m.company));
    var score = 0;
    if (sub && mt === sub) score += 10;
    if (comp && mc === comp) score += 8;
    // Exact subject alone is enough; both together is strongest
    if (score > bestScore) {
      bestScore = score;
      best = m;
    }
  });

  if (sub && comp && bestScore >= 18) return best;
  if (sub && bestScore >= 10) return best;
  return null;
}

function isStaticTestText_(subject) {
  var s = normMatch_(subject);
  if (!s) return false;
  var blocked = ['webhook trigger test', 'field mapping check'];
  for (var i = 0; i < blocked.length; i++) {
    if (s.indexOf(blocked[i]) >= 0) return true;
  }
  return false;
}

function rowModifiedAt_(m) {
  m = m || {};
  if (m.rowInfo && m.rowInfo.lastModifiedAt) return m.rowInfo.lastModifiedAt;
  if (m.rowInfo && m.rowInfo.updatedAt) return m.rowInfo.updatedAt;
  return m['rowInfo.lastModifiedAt'] || m['rowInfo.updatedAt'] || '';
}

function parseRaynetTime_(s) {
  s = String(s || '').trim();
  if (!s) return 0;
  var d = new Date(s.replace(' ', 'T'));
  return isNaN(d.getTime()) ? 0 : d.getTime();
}

function normMatch_(s) {
  return String(s || '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function apiGet_(path) {
  try {
    var res = UrlFetchApp.fetch('https://app.raynet.cz/api/v2' + path, {
      method: 'get',
      headers: apiHeaders_(),
      muteHttpExceptions: true,
    });
    if (res.getResponseCode() !== 200) {
      return { ok: false, error: 'HTTP ' + res.getResponseCode() + ' — check RAYNET_USER, RAYNET_API_KEY, RAYNET_INSTANCE=ucs' };
    }
    var body = JSON.parse(res.getContentText());
    var data = body.data;
    if (Array.isArray(data)) return { ok: true, data: data };
    return { ok: true, data: data || body };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

function apiHeaders_() {
  var p = PropertiesService.getScriptProperties();
  var h = {
    Authorization: 'Basic ' + Utilities.base64Encode(
      p.getProperty('RAYNET_USER').trim() + ':' + p.getProperty('RAYNET_API_KEY').trim()
    ),
    Accept: 'application/json',
  };
  if (p.getProperty('RAYNET_INSTANCE_ID')) h['X-Instance-Id'] = p.getProperty('RAYNET_INSTANCE_ID');
  else if (p.getProperty('RAYNET_INSTANCE')) h['X-Instance-Name'] = p.getProperty('RAYNET_INSTANCE');
  return h;
}

// ─── Log ─────────────────────────────────────────────────────────────────────

function logRow_(status, f, out) {
  var errMsg = out.error || out.draft_error || '';
  var docInfo = (out.doc_ids && out.doc_ids.length)
    ? (out.retrieval || '') + ': ' + out.doc_ids.join(', ')
    : (out.retrieval || '');
  if (docInfo && errMsg) errMsg = docInfo + ' | ' + errMsg;
  else if (docInfo) errMsg = docInfo;
  backupLog_(status, f, errMsg);
  try {
    getLogSheet_().appendRow([
      new Date(), status,
      f.company || '', f.subject || '', f.scheduled_from || '',
      f.questions || '', f.meeting_id || '', f.source || '',
      out.draft_created ? 'YES' : 'NO',
      errMsg,
      f.match_note || '',
    ]);
  } catch (e) {
    PropertiesService.getScriptProperties().setProperty('LAST_WEBHOOK_LOG_ERROR', String(e));
    Logger.log('logRow_ FAILED: ' + e + ' — run saveSpreadsheetId_() from UCS-Knowledge-Base sheet');
  }
}

/** Always works — even if Webhook-Log sheet is missing. */
function backupLog_(status, f, errMsg) {
  PropertiesService.getScriptProperties().setProperties({
    LAST_WEBHOOK_AT: String(new Date()),
    LAST_WEBHOOK_STATUS: String(status || ''),
    LAST_WEBHOOK_COMPANY: String((f && f.company) || ''),
    LAST_WEBHOOK_SUBJECT: String((f && f.subject) || ''),
    LAST_WEBHOOK_DRAFT: String((f && f.source) || ''),
    LAST_WEBHOOK_ERROR: String(errMsg || ''),
  });
}

/** Run after editing a RAYNET meeting — tells you exactly what happened. */
function whereIsMyDraft() {
  var p = PropertiesService.getScriptProperties();
  var lines = [
    '=== Where is my draft? ===',
    'Last webhook received: ' + (p.getProperty('LAST_WEBHOOK_AT') || 'NEVER — RAYNET did not call Apps Script'),
    'Last status: ' + (p.getProperty('LAST_WEBHOOK_STATUS') || '—'),
    'Last company: ' + (p.getProperty('LAST_WEBHOOK_COMPANY') || '—'),
    'Last subject: ' + (p.getProperty('LAST_WEBHOOK_SUBJECT') || '—'),
    'Last source: ' + (p.getProperty('LAST_WEBHOOK_DRAFT') || '—'),
    'Last error: ' + (p.getProperty('LAST_WEBHOOK_ERROR') || '—'),
    'Sheet log error: ' + (p.getProperty('LAST_WEBHOOK_LOG_ERROR') || 'none'),
    '',
    'If "NEVER" → fix RAYNET automation (see checklist below in Execution log).',
    'If status OK/EMPTY but no Gmail draft → check Drafts on: ' + (p.getProperty('DRAFT_EMAIL') || DEFAULT_EMAIL),
    'Gmail drafts are created under the account that deployed the web app (Execute as Me).',
  ];
  if (p.getProperty('LAST_WEBHOOK_AT') === null) {
    lines.push('');
    lines.push('RAYNET checklist:');
    lines.push('1. Automations → your automation → toggle ON (green)');
    lines.push('2. Trigger = Meeting is edited → SAVE step 1');
    lines.push('3. Remove ALL conditions temporarily (for testing)');
    lines.push('4. Only selected users = OFF');
    lines.push('5. Webhook URL ends with ?secret=ucs-demo-secret');
    lines.push('6. Open meeting → change Subject → click green SAVE (not just close popup)');
    lines.push('7. Apps Script → Executions → look for doPost within 60 sec');
  }
  Logger.log(lines.join('\n'));
  return lines.join('\n');
}

function getSpreadsheet_() {
  var props = PropertiesService.getScriptProperties();
  var id = props.getProperty('SPREADSHEET_ID');
  if (id) return SpreadsheetApp.openById(id);
  var active = SpreadsheetApp.getActiveSpreadsheet();
  if (active) {
    props.setProperty('SPREADSHEET_ID', active.getId());
    return active;
  }
  throw new Error('No spreadsheet — open UCS-Knowledge-Base and run saveSpreadsheetId_()');
}

function getLogSheet_() {
  var ss = getSpreadsheet_();
  var sh = ss.getSheetByName(LOG_SHEET);
  if (!sh) {
    sh = ss.insertSheet(LOG_SHEET);
    sh.appendRow([
      'timestamp', 'status', 'company', 'subject', 'meeting_date',
      'questions', 'meeting_id', 'source', 'draft', 'error', 'match_note',
    ]);
    sh.setFrozenRows(1);
  }
  return sh;
}

// ─── Parse webhook ───────────────────────────────────────────────────────────

function parseJson_(body, e) {
  var raw = {};
  if (body) {
    try { raw = JSON.parse(body); } catch (ignore) {
      body.split('&').forEach(function (p) {
        var kv = p.split('=');
        if (kv[0]) raw[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || '');
      });
    }
  } else if (e.parameter) raw = e.parameter;

  if (raw.type === 'workflow.event') raw._workflow_event = true;
  if (raw.data && typeof raw.data === 'object') {
    Object.keys(raw.data).forEach(function (k) {
      if (k && raw.data[k] != null) raw[k] = raw.data[k];
    });
  }
  return raw;
}

function coalesce_(raw) {
  if (!raw.title) raw.title = first_(raw.Title, raw.Subject, raw.discussion_topics, raw.subject);
  if (!raw.scheduledFrom) {
    raw.scheduledFrom = first_(raw['Scheduled From'], raw['Date from'], raw.scheduledFrom, raw.meeting_date);
  }
  if (!raw.scheduledTill) {
    raw.scheduledTill = first_(raw['Scheduled Till'], raw['Date to'], raw.scheduledTill);
  }
  if (!raw.description) {
    raw.description = first_(raw.Description, raw['Questions to Discuss'], raw.notes, raw.meeting_report);
  }
  if (!raw.solution) raw.solution = first_(raw.Outcome, raw['Meeting Outcome'], raw.meeting_outcome);
  if (!raw.company) raw.company = first_(raw.Company, raw.Account, raw.account, raw.company);
  if (!raw.status) raw.status = first_(raw.Status, raw.status);
  if (!raw._field_source) raw._field_source = 'webhook';
  return raw;
}

function isRecordEvent_(raw) {
  var t = String((raw && raw.type) || '').toLowerCase();
  return t === 'record.created' || t === 'record.updated' || t === 'record.deleted';
}

function isWorkflowPing_(raw) {
  return !!(raw && (raw.type === 'workflow.event' || raw.eventId || raw._workflow_event));
}

function emptyDraftHelp_(raw) {
  raw = raw || {};
  var lines = [
    'WHY EMPTY: "Calender Meeting Tracker" sends workflow.event only — no meeting fields inside.',
    '',
  ];
  if (!hasApi_()) {
    lines.push('MISSING: RAYNET API not configured in Script properties.');
    lines.push('Add: RAYNET_USER, RAYNET_API_KEY, RAYNET_INSTANCE = ucs');
    lines.push('Then save meeting again — script will load full meeting from API.');
  } else if (raw._api_error) {
    lines.push('API ERROR: ' + raw._api_error);
    lines.push('Fix API key at RAYNET → Settings → For Developers → API Keys');
  }
  lines.push('');
  lines.push('OR fix Automation → Send webhook → map these keys to Meeting fields:');
  lines.push('company, discussion_topics, description, meeting_date, meeting_id');
  return lines.join('\n');
}

function getSecret_() {
  return PropertiesService.getScriptProperties().getProperty('WEBHOOK_SECRET') || DEFAULT_SECRET;
}

/** Run after wrong meeting in draft — compares webhook vs API in last log row. */
function whyWrongMeeting() {
  var sh = getLogSheet_();
  if (!sh || sh.getLastRow() < 2) {
    Logger.log('No Webhook-Log rows yet.');
    return;
  }
  var r = sh.getRange(sh.getLastRow(), 1, sh.getLastRow(), 11).getValues()[0];
  var lines = [
    '=== Last webhook run ===',
    'Time:     ' + r[0],
    'Status:   ' + r[1],
    'Company:  ' + r[2],
    'Subject:  ' + r[3],
    'Source:   ' + r[7],
    'Draft:    ' + r[8],
    'Error:    ' + r[9],
    'Match:    ' + (r[10] || '—'),
    '',
  ];
  var p = PropertiesService.getScriptProperties();
  var body = p.getProperty('LAST_WEBHOOK_BODY') || '';
  lines.push('Last webhook body (first 500 chars):');
  lines.push(body.substring(0, 500));
  lines.push('');
  if (String(r[7]).indexOf('just_saved') >= 0) {
    lines.push('Used meeting modified in last 3 min — should be the one you saved.');
  } else if (String(r[7]).indexOf('webhook_match') >= 0) {
    lines.push('Matched by subject+company — if wrong, webhook sent wrong Subject/Account.');
  } else if (String(r[1]) === 'OK' && String(r[7]).indexOf('raynet_api') < 0) {
    lines.push('PROBLEM: Used webhook fields only, not API — check RAYNET API properties.');
  }
  lines.push('');
  lines.push('FIX in RAYNET Send webhook — add row: meeting_id = {Meeting → ID} if available');
  lines.push('Or verify discussion_topics = {Subject} and company = {Account} use { } picker.');
  Logger.log(lines.join('\n'));
  return lines.join('\n');
}

/** Run after UNAUTHORIZED — shows exact payload RAYNET sent. */
function inspectLastWebhook() {
  var p = PropertiesService.getScriptProperties();
  Logger.log('=== Last RAYNET webhook ===');
  Logger.log('Time: ' + (p.getProperty('LAST_WEBHOOK_BODY_AT') || 'never'));
  Logger.log('URL params: ' + (p.getProperty('LAST_WEBHOOK_PARAMS') || 'none'));
  Logger.log('Body: ' + (p.getProperty('LAST_WEBHOOK_BODY') || 'empty'));
  Logger.log('');
  Logger.log('Fix: RAYNET → Automation webhooks → URL ends with ?secret=ucs-demo-secret');
  Logger.log('And Send webhook → add row: webhook_secret = ucs-demo-secret (type text, not variable)');
  return {
    params: p.getProperty('LAST_WEBHOOK_PARAMS'),
    body: p.getProperty('LAST_WEBHOOK_BODY'),
  };
}

function saveLastBody_(body, e) {
  e = e || {};
  var props = PropertiesService.getScriptProperties();
  props.setProperty('LAST_WEBHOOK_BODY_AT', String(new Date()));
  props.setProperty('LAST_WEBHOOK_BODY', String(body || '').substring(0, 2000));
  props.setProperty('LAST_WEBHOOK_PARAMS', JSON.stringify(e.parameter || {}));
}

function checkSecret_(e, body) {
  var secret = getSecret_();
  e = e || {};

  // OpenAPI webhooks send X-RAYNETCRM-Token in a header (Apps Script cannot read it).
  // Register the webhook URL with ?secret=ucs-demo-secret so auth works via query string.
  if (body) {
    try {
      var parsed = JSON.parse(body);
      if (isRecordEvent_(parsed) && e.parameter && String(e.parameter.secret || '').trim() === secret) {
        return true;
      }
    } catch (ignore) {}
  }

  if (e.parameter) {
    var paramKeys = ['secret', 'webhook_secret', 'WEBHOOK_SECRET'];
    for (var i = 0; i < paramKeys.length; i++) {
      if (String(e.parameter[paramKeys[i]] || '').trim() === secret) return true;
    }
  }

  if (body) {
    try {
      if (secretInObject_(JSON.parse(body), secret)) return true;
    } catch (ignore) {
      if (body.indexOf('webhook_secret') >= 0 && body.indexOf(secret) >= 0) return true;
      if (body.indexOf('secret') >= 0 && body.indexOf(secret) >= 0) return true;
    }
  }
  return false;
}

function secretInObject_(obj, secret) {
  if (!obj || typeof obj !== 'object') return false;
  var keys = ['webhook_secret', 'secret', 'WEBHOOK_SECRET'];
  for (var i = 0; i < keys.length; i++) {
    if (String(obj[keys[i]] || '').trim() === secret) return true;
  }
  if (obj.data && secretInObject_(obj.data, secret)) return true;
  var k;
  for (k in obj) {
    if (obj.hasOwnProperty(k) && typeof obj[k] === 'object' && secretInObject_(obj[k], secret)) return true;
  }
  return false;
}

function getBody_(e) {
  if (e.postData && e.postData.contents) return String(e.postData.contents);
  if (e.parameter && Object.keys(e.parameter).length) return JSON.stringify(e.parameter);
  return '';
}

// ─── Small helpers ───────────────────────────────────────────────────────────

function meetingId_(raw) {
  raw = raw || {};
  var nested = (raw.data && typeof raw.data === 'object') ? raw.data : {};
  return String(first_(
    raw.meeting_id, raw.meetingId, raw.entityId, raw.entity_id,
    raw.id, raw.Id, raw.ID,
    raw.activityId, raw.activity_id, raw.recordId,
    nested.meeting_id, nested.entityId, nested.id, nested.activityId
  ) || '').replace(/\D/g, '');
}

function companyName_(c) {
  if (!c) return '';
  if (typeof c === 'object') return String(c.name || c.title || '').trim();
  return String(c).trim();
}

function personName_(p) {
  if (!p || typeof p !== 'object') return String(p || '').trim();
  return String(p.fullName || p.name || '').trim();
}

function personDetail_(p) {
  if (!p) return '';
  if (typeof p !== 'object') return String(p).trim();
  var name = personName_(p);
  var extra = [];
  if (p.company && p.company.name) extra.push(p.company.name);
  if (p.role) extra.push(p.role);
  var email = p.email || '';
  var line = name;
  if (extra.length) line += ' (' + extra.join(', ') + ')';
  if (email) line += ' <' + email + '>';
  return line.trim();
}

function enumLabel_(v) {
  if (v == null || v === '') return '';
  if (typeof v === 'object') {
    return String(v.value || v.name || v.caption || v.label || '').trim();
  }
  return String(v).trim();
}

function formatLocation_(loc) {
  if (!loc) return '';
  if (typeof loc === 'string') return loc.trim();
  if (typeof loc === 'object') {
    return first_(
      loc.name,
      loc.address,
      [loc.street, loc.city, loc.country].filter(Boolean).join(', ')
    ) || '';
  }
  return String(loc).trim();
}

function formatTags_(tags) {
  if (!tags) return '';
  if (Array.isArray(tags)) {
    return tags.map(function (t) { return enumLabel_(t) || String(t); }).filter(Boolean).join(', ');
  }
  return enumLabel_(tags);
}

function formatParticipants_(parts) {
  if (!parts) return '';
  if (Array.isArray(parts)) {
    return parts.map(function (p) {
      return personDetail_(p.person || p);
    }).filter(Boolean).join('; ');
  }
  return personDetail_(parts);
}

function calcDuration_(from, till) {
  from = String(from || '').trim();
  till = String(till || '').trim();
  if (!from || !till) return '';
  try {
    var d1 = new Date(from.replace(' ', 'T'));
    var d2 = new Date(till.replace(' ', 'T'));
    if (isNaN(d1.getTime()) || isNaN(d2.getTime())) return '';
    var mins = Math.round((d2 - d1) / 60000);
    if (mins <= 0) return '';
    var h = Math.floor(mins / 60);
    var m = mins % 60;
    if (h && m) return h + 'h ' + m + 'm';
    if (h) return h + ' hour' + (h > 1 ? 's' : '');
    return m + ' min';
  } catch (ignore) {
    return '';
  }
}

function stripHtml_(t) {
  return String(t || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

function parseDate_(v) {
  v = String(v || '').trim();
  var m = v.match(/^(\d{4}-\d{2}-\d{2})/);
  if (m) return m[1];
  m = v.match(/^(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})/);
  if (m) return m[3] + '-' + ('0' + m[2]).slice(-2) + '-' + ('0' + m[1]).slice(-2);
  return '';
}

function parseDateTime_(v) {
  v = String(v || '').trim();
  if (!v) return '';
  var iso = v.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{1,2}):(\d{2}))?/);
  if (iso) {
    var out = parseInt(iso[3], 10) + '.' + parseInt(iso[2], 10) + '.' + iso[1];
    if (iso[4]) out += ' ' + iso[4] + ':' + iso[5];
    return out;
  }
  var eu = v.match(/^(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})(?:\s+(\d{1,2}):(\d{2}))?/);
  if (eu) {
    var euOut = eu[1] + '.' + eu[2] + '.' + eu[3];
    if (eu[4]) euOut += ' ' + eu[4] + ':' + eu[5];
    return euOut;
  }
  return v.replace('T', ' ').substring(0, 16);
}

function first_() {
  for (var i = 0; i < arguments.length; i++) {
    var v = String(arguments[i] || '').trim();
    if (v && v !== '[object Object]') return arguments[i];
  }
  return '';
}

function esc_(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function text_(msg) {
  return ContentService.createTextOutput(String(msg))
    .setMimeType(ContentService.MimeType.TEXT);
}
