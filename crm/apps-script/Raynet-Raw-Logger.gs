/**
 * RAYNET webhook raw logger + OpenAPI meeting fetch (Fix 2 + Fix 3).
 *
 * Tabs:
 *   Webhook-Raw  — what RAYNET automation POST sent
 *   Meeting-API  — full meeting from GET /api/v2/meeting/{id}/ (OpenAPI)
 *
 * Script properties (Fix 2):
 *   RAYNET_USER, RAYNET_API_KEY, RAYNET_INSTANCE=ucs
 *   WEBHOOK_SECRET=ucs-demo-secret
 *   SPREADSHEET_ID (optional)
 *
 * Deploy: Execute as Me, Anyone — URL ends with ?secret=ucs-demo-secret
 */

var DEFAULT_SECRET = 'ucs-demo-secret';
var SPREADSHEET_ID_FALLBACK = '1Gr30Y3HSdD85AsOpjbLUNXvVW3QgFCXDqSborzDFEeI';
var RAW_LOG_SHEET = 'Webhook-Raw';
var API_LOG_SHEET = 'Meeting-API';
var RAW_FIELDS = ['company', 'discussion_topics', 'description', 'meeting_date', 'meeting_id', 'webhook_secret'];

function doGet(e) {
  e = e || {};
  if (String(e.parameter && e.parameter.secret || '') !== getSecret_()) {
    return text_('UNAUTHORIZED — add ?secret=ucs-demo-secret to the URL');
  }
  return text_('OK — Webhook-Raw + Meeting-API logger ready.');
}

function doPost(e) {
  e = e || {};
  var body = getBody_(e);
  if (!checkSecret_(e, body)) {
    return json_({ status: 'unauthorized' });
  }

  var raw = parseJson_(body, e);
  appendRawRow_(raw, body);

  var apiRow = fetchApiMeetingRow_(raw);
  appendApiRow_(apiRow);

  return json_({ status: 'ok', webhook: raw, api: apiRow });
}

// ─── Fix 2: OpenAPI GET /meeting/{id}/ or latest ───────────────────────────

function fetchApiMeetingRow_(raw) {
  if (!hasApi_()) {
    return errorRow_('Set RAYNET_USER, RAYNET_API_KEY, RAYNET_INSTANCE=ucs', raw);
  }
  var res = fetchMeetingForWebhook_(raw);
  if (res.ok) {
    var row = mapApiToRow_(res.data, res.source || 'raynet_api');
    row.webhook_subject = webhookSubject_(raw);
    row.webhook_company = webhookCompany_(raw);
    row.match_note = res.match_note || '';
    return row;
  }
  return errorRow_(res.error || 'No meeting matched', raw);
}

function errorRow_(msg, raw) {
  return {
    source: 'ERROR',
    id: '', title: '', company: '', scheduledFrom: '', scheduledTill: '',
    description: '', solution: '', status: '', owner: '',
    webhook_subject: webhookSubject_(raw),
    webhook_company: webhookCompany_(raw),
    match_note: '',
    error: msg,
  };
}

/** Never guess GenAgro — match webhook fields or return ERROR. */
function fetchMeetingForWebhook_(raw) {
  raw = raw || {};
  var subject = webhookSubject_(raw);
  var company = webhookCompany_(raw);

  var id = meetingId_(raw);
  if (id) {
    var byId = apiGet_('/meeting/' + id + '/');
    if (byId.ok) {
      return { ok: true, data: byId.data, source: 'raynet_api_id', match_note: 'matched by meeting_id=' + id };
    }
    return { ok: false, error: 'GET /meeting/' + id + ' failed: ' + (byId.error || '') };
  }

  if (!subject && !company) {
    return {
      ok: false,
      error: 'WEBHOOK_EMPTY — RAYNET sent no Subject/Account. In Send webhook map: '
        + 'discussion_topics=Meeting→Subject, company=Meeting→Account (use { } picker, not typed text)',
    };
  }

  if (isStaticTestText_(subject)) {
    var recentRes = fetchJustSavedMeeting_(list);
    if (recentRes.ok) {
      return {
        ok: true, data: recentRes.data, source: 'raynet_api_just_saved',
        match_note: 'RAYNET sent static test text — used meeting modified in last 5 min: "'
          + (recentRes.data.title || '') + '"',
      };
    }
    return {
      ok: false,
      error: 'WEBHOOK_STATIC_TEXT — RAYNET still sends test payload ("' + subject
        + '"). The static text is stored in "Calender Meeting Tracker" webhook registration. '
        + 'DELETE that webhook, create NEW one (URL only), rebuild automation. '
        + 'Or save meeting then retry within 5 min for just_saved fallback.',
    };
  }

  var listRes = apiGet_(
    '/meeting/?offset=0&limit=100&sortColumn=rowInfo.lastModifiedAt&sortDirection=DESC'
  );
  if (!listRes.ok) return listRes;
  var list = listRes.data || [];
  if (!list.length) return { ok: false, error: 'No meetings in RAYNET API' };

  var matched = pickMeetingMatch_(list, subject, company);
  if (matched) {
    var full = apiGet_('/meeting/' + matched.id + '/');
    if (full.ok) {
      return {
        ok: true, data: full.data, source: 'raynet_api_webhook_match',
        match_note: 'matched title="' + (matched.title || '') + '" company="' + companyName_(matched.company) + '"',
      };
    }
  }

  return {
    ok: false,
    error: 'NO_MATCH — webhook sent subject="' + subject + '" company="' + company
      + '" but no RAYNET meeting matched. Save the meeting with THAT exact Subject, or fix webhook variables.',
  };
}

function isStaticTestText_(subject) {
  var s = norm_(subject);
  if (!s) return false;
  var blocked = [
    'webhook trigger test',
    'field mapping check',
    'webhook trigger test - field mapping check',
  ];
  for (var i = 0; i < blocked.length; i++) {
    if (s.indexOf(blocked[i]) >= 0) return true;
  }
  return false;
}

function webhookSubject_(raw) {
  return String(raw.discussion_topics || raw.title || raw.subject || '').trim();
}

function webhookCompany_(raw) {
  return companyName_(raw.company || raw.account || raw.Account);
}

function pickMeetingMatch_(list, subject, company) {
  var sub = norm_(subject);
  var comp = norm_(company);
  var best = null;
  var bestScore = 0;

  list.forEach(function (m) {
    var score = 0;
    var mTitle = norm_(m.title || '');
    var mComp = norm_(companyName_(m.company));
    if (sub && mTitle === sub) score += 10;
    else if (sub && mTitle.indexOf(sub) >= 0) score += 6;
    else if (sub && sub.indexOf(mTitle) >= 0 && mTitle) score += 4;
    if (comp && mComp === comp) score += 8;
    else if (comp && mComp.indexOf(comp) >= 0) score += 4;
    if (score > bestScore) {
      bestScore = score;
      best = m;
    }
  });

  return bestScore >= 4 ? best : null;
}

function pickRecentlyModified_(list, withinMinutes) {
  withinMinutes = withinMinutes || 20;
  var cutoff = Date.now() - withinMinutes * 60 * 1000;
  for (var i = 0; i < list.length; i++) {
    var t = parseRaynetTime_(rowModifiedAt_(list[i]));
    if (t && t >= cutoff) return list[i];
  }
  return null;
}

function fetchJustSavedMeeting_(list) {
  list = list || [];
  var recent = pickRecentlyModified_(list, 5);
  if (!recent || !recent.id) return { ok: false };
  var full = apiGet_('/meeting/' + recent.id + '/');
  if (!full.ok) return { ok: false };
  return { ok: true, data: full.data };
}

function rowModifiedAt_(m) {
  m = m || {};
  if (m.rowInfo && m.rowInfo.lastModifiedAt) return m.rowInfo.lastModifiedAt;
  if (m.rowInfo && m.rowInfo.updatedAt) return m.rowInfo.updatedAt;
  return m['rowInfo.lastModifiedAt'] || m['rowInfo.updatedAt'] || m.scheduledFrom || '';
}

function parseRaynetTime_(s) {
  s = String(s || '').trim();
  if (!s) return 0;
  var d = new Date(s.replace(' ', 'T'));
  return isNaN(d.getTime()) ? 0 : d.getTime();
}

function norm_(s) {
  return String(s || '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function fetchLatestMeeting_() {
  return fetchMeetingForWebhook_({});
}

function mapApiToRow_(d, source) {
  d = d || {};
  return {
    source: source,
    id: d.id || '',
    title: d.title || '',
    company: companyName_(d.company),
    scheduledFrom: d.scheduledFrom || '',
    scheduledTill: d.scheduledTill || '',
    description: d.description || '',
    solution: d.solution || '',
    status: enumLabel_(d.status),
    owner: personName_(d.owner),
    webhook_subject: '',
    webhook_company: '',
    match_note: '',
    error: '',
  };
}

function hasApi_() {
  var p = PropertiesService.getScriptProperties();
  return !!(p.getProperty('RAYNET_USER') && p.getProperty('RAYNET_API_KEY') &&
    (p.getProperty('RAYNET_INSTANCE') || p.getProperty('RAYNET_INSTANCE_ID')));
}

function apiGet_(path) {
  try {
    var res = UrlFetchApp.fetch('https://app.raynet.cz/api/v2' + path, {
      method: 'get',
      headers: apiHeaders_(),
      muteHttpExceptions: true,
    });
    if (res.getResponseCode() !== 200) {
      return { ok: false, error: 'HTTP ' + res.getResponseCode() };
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

// ─── Fix 3: log webhook + full JSON + object-safe cells ──────────────────────

function appendRawRow_(raw, body) {
  var sh = getSheet_(RAW_LOG_SHEET, ['timestamp'].concat(RAW_FIELDS).concat(['raw_json']));
  var row = [new Date()];
  RAW_FIELDS.forEach(function (key) {
    row.push(cellValue_(raw[key]));
  });
  row.push(String(body || JSON.stringify(raw)).substring(0, 50000));
  sh.appendRow(row);
}

function appendApiRow_(r) {
  r = r || {};
  var headers = ['timestamp', 'source', 'id', 'title', 'company', 'scheduledFrom', 'scheduledTill',
    'description', 'solution', 'status', 'owner', 'webhook_subject', 'webhook_company', 'match_note', 'error'];
  var sh = getSheet_(API_LOG_SHEET, headers);
  sh.appendRow([
    new Date(), r.source || '', r.id || '', r.title || '', r.company || '',
    r.scheduledFrom || '', r.scheduledTill || '', r.description || '', r.solution || '',
    r.status || '', r.owner || '', r.webhook_subject || '', r.webhook_company || '',
    r.match_note || '', r.error || '',
  ]);
}

/** Run after a test save — explains why GenAgro appeared. */
function whyWrongMeeting() {
  var ss = getSpreadsheet_();
  var rawSh = ss.getSheetByName(RAW_LOG_SHEET);
  var apiSh = ss.getSheetByName(API_LOG_SHEET);
  var lines = ['=== Why wrong meeting? ==='];
  if (!rawSh || rawSh.getLastRow() < 2) {
    lines.push('No Webhook-Raw rows yet.');
    Logger.log(lines.join('\n'));
    return;
  }
  var rawCols = rawSh.getLastColumn();
  var raw = rawSh.getRange(rawSh.getLastRow(), 1, rawSh.getLastRow(), rawCols).getValues()[0];
  lines.push('Webhook-Raw last row:');
  lines.push('  company: ' + raw[1]);
  lines.push('  discussion_topics: ' + raw[2]);
  lines.push('  description (first 80): ' + String(raw[3]).substring(0, 80));
  if (apiSh && apiSh.getLastRow() >= 2) {
    var api = apiSh.getRange(apiSh.getLastRow(), 1, apiSh.getLastRow(), 15).getValues()[0];
    lines.push('Meeting-API last row:');
    lines.push('  source: ' + api[1]);
    lines.push('  title: ' + api[3]);
    lines.push('  company: ' + api[4]);
    lines.push('  webhook_subject: ' + api[11]);
    lines.push('  error: ' + api[14]);
  }
  lines.push('');
  if (String(raw[2]).indexOf('Webhook trigger test') >= 0) {
    lines.push('PROBLEM: discussion_topics is STATIC TEST TEXT in RAYNET — not {Subject} variable.');
  }
  if (!raw[1] && !raw[2]) {
    lines.push('PROBLEM: Webhook sent empty company + subject — fix RAYNET mapping.');
  }
  lines.push('FIX: RAYNET → Send webhook → discussion_topics = {Meeting→Subject}, company = {Meeting→Account}');
  Logger.log(lines.join('\n'));
}

function cellValue_(v) {
  if (v == null || v === '') return '';
  if (typeof v === 'object') {
    return String(v.name || v.fullName || v.title || v.value || JSON.stringify(v));
  }
  return String(v);
}

function getSheet_(name, headers) {
  var ss = getSpreadsheet_();
  var sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.appendRow(headers);
    sh.setFrozenRows(1);
  }
  return sh;
}

function getSpreadsheet_() {
  var props = PropertiesService.getScriptProperties();
  var id = props.getProperty('SPREADSHEET_ID') || SPREADSHEET_ID_FALLBACK;
  return SpreadsheetApp.openById(id);
}

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

  if (raw.data && typeof raw.data === 'object') {
    Object.keys(raw.data).forEach(function (k) {
      if (k && raw.data[k] != null) raw[k] = raw.data[k];
    });
  }
  return raw;
}

function meetingId_(raw) {
  raw = raw || {};
  return String(raw.meeting_id || raw.meetingId || raw.id || raw.Id || '').replace(/\D/g, '');
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

function enumLabel_(v) {
  if (v == null) return '';
  if (typeof v === 'object') return String(v.value || v.name || '').trim();
  return String(v).trim();
}

function getSecret_() {
  return PropertiesService.getScriptProperties().getProperty('WEBHOOK_SECRET') || DEFAULT_SECRET;
}

function checkSecret_(e, body) {
  var secret = getSecret_();
  e = e || {};
  if (e.parameter && String(e.parameter.secret || '').trim() === secret) return true;
  if (e.parameter && String(e.parameter.webhook_secret || '').trim() === secret) return true;
  if (body) {
    try {
      var p = JSON.parse(body);
      if (String(p.webhook_secret || p.secret || '').trim() === secret) return true;
      if (p.data && String(p.data.webhook_secret || '').trim() === secret) return true;
    } catch (ignore) {
      if (body.indexOf(secret) >= 0) return true;
    }
  }
  return false;
}

function getBody_(e) {
  if (e.postData && e.postData.contents) return String(e.postData.contents);
  if (e.parameter && Object.keys(e.parameter).length) return JSON.stringify(e.parameter);
  return '';
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function text_(msg) {
  return ContentService.createTextOutput(String(msg))
    .setMimeType(ContentService.MimeType.TEXT);
}

/** Run in Apps Script to verify OpenAPI credentials (Fix 2). */
function testRaynetApi() {
  var diag = diagnoseRaynetApi_();
  Logger.log(diag.report);
  if (!diag.ok) throw new Error(diag.report);
  Logger.log(JSON.stringify(mapApiToRow_(diag.meeting, 'test'), null, 2));
}

/** Detailed 401 help — run this if testRaynetApi fails. */
function diagnoseRaynetApi_() {
  var p = PropertiesService.getScriptProperties();
  var user = String(p.getProperty('RAYNET_USER') || '').trim();
  var key = String(p.getProperty('RAYNET_API_KEY') || '').trim();
  var instance = String(p.getProperty('RAYNET_INSTANCE') || '').trim();
  var instanceId = String(p.getProperty('RAYNET_INSTANCE_ID') || '').trim();
  var lines = ['=== RAYNET API diagnosis ==='];

  if (!user) lines.push('MISSING: RAYNET_USER');
  else lines.push('RAYNET_USER: ' + user);

  if (!key) lines.push('MISSING: RAYNET_API_KEY');
  else if (!key.startsWith('crm-')) lines.push('WARN: RAYNET_API_KEY should start with crm- (you may have the masked key)');
  else lines.push('RAYNET_API_KEY: set (' + key.length + ' chars, starts crm-)');

  if (!instance && !instanceId) lines.push('MISSING: RAYNET_INSTANCE or RAYNET_INSTANCE_ID');
  else lines.push('RAYNET_INSTANCE: ' + (instance || '(using ID)') + (instanceId ? ' | ID: ' + instanceId : ''));

  if (!user || !key || (!instance && !instanceId)) {
    return { ok: false, report: lines.join('\n') + '\n\nFix Script properties first.' };
  }

  var res = apiGet_('/meeting/?offset=0&limit=1');
  if (res.ok) {
    lines.push('API test: OK (HTTP 200)');
    return { ok: true, report: lines.join('\n'), meeting: res.data && res.data[0] ? res.data[0] : res.data };
  }

  lines.push('API test: FAILED — ' + (res.error || 'unknown'));
  lines.push('');
  lines.push('HTTP 401 fix checklist:');
  lines.push('1. RAYNET_USER = login email of API key user (Nikola) — NOT "Agent Integration"');
  lines.push('   Expected: n.avramovic@unifiedcloudsensors.com');
  lines.push('2. RAYNET_API_KEY = FULL key from Settings → For Developers → API Keys');
  lines.push('   Must start with crm- — regenerate if you only have crm-****AJrg masked');
  lines.push('3. RAYNET_INSTANCE = ucs (from URL app.raynet.cz/ucs/)');
  lines.push('4. No spaces before/after values in Script properties');
  lines.push('5. API key user must match RAYNET_USER exactly');
  return { ok: false, report: lines.join('\n') };
}
