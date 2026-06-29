/**
 * Deploy as Web App (Execute as: Me, Access: Anyone) to send emails via Gmail.
 * No SMTP / App Password needed.
 *
 * Script properties:
 *   EMAIL_WEBHOOK_SECRET = same value as GMAIL_WEBAPP_SECRET in .env
 *
 * After deploy, copy the Web App URL into .env as GMAIL_WEBAPP_URL
 */
function doPost(e) {
  try {
    const expected = PropertiesService.getScriptProperties().getProperty('EMAIL_WEBHOOK_SECRET');
    const data = JSON.parse(e.postData.contents);
    if (!expected || data.secret !== expected) {
      return json_(401, { error: 'unauthorized' });
    }
    if (!data.to || !data.subject || !data.body) {
      return json_(400, { error: 'Missing to, subject, or body' });
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
    return json_(200, { sent: true, to: data.to });
  } catch (err) {
    return json_(500, { error: String(err) });
  }
}

function json_(code, body) {
  const out = ContentService.createTextOutput(JSON.stringify(body)).setMimeType(
    ContentService.MimeType.JSON
  );
  // Web App doPost cannot set HTTP status codes; include code in JSON body.
  return out;
}

/** Run once locally to verify Gmail send works */
function testSendDirect() {
  GmailApp.sendEmail(
    Session.getActiveUser().getEmail(),
    'UCS test email',
    'If you receive this, GmailApp sending works without SMTP.'
  );
  Logger.log('Test sent to ' + Session.getActiveUser().getEmail());
}
