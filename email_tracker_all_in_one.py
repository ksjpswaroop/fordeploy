import os
import re
import json
import base64
import sqlite3
import datetime as dt
from typing import Optional, List, Dict, Any, Tuple
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Email, To, Content,
    TrackingSettings, ClickTracking, OpenTracking,
    MailSettings, SandBoxMode, Personalization, CustomArg
)
import uvicorn

# --- NEW: IMAP + email parsing ---
import imaplib
import email as pyemail
from email.header import decode_header
from email.utils import parsedate_to_datetime, parseaddr

# Optional: signature verification for Event Webhook
try:
    from sendgrid.helpers.eventwebhook import EventWebhook, EventWebhookHeader
    HAVE_VERIFY = True
except Exception:
    HAVE_VERIFY = False

# ---------------------- ENV ----------------------
load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
FROM_EMAIL       = os.getenv("SENDGRID_FROM_EMAIL", "").strip() or os.getenv("FROM_EMAIL", "").strip()
FROM_NAME        = os.getenv("SENDGRID_FROM_NAME", "").strip()
REPLY_TO_EMAIL   = os.getenv("REPLY_TO_EMAIL", "").strip()  # optional, recommended to point replies to your IMAP inbox

BASE_URL         = (os.getenv("BASE_URL") or "http://127.0.0.1:8001").rstrip("/")
DB_PATH          = os.getenv("TRACKING_DB_PATH", "events.db")
DEFAULT_SANDBOX  = os.getenv("SENDGRID_SANDBOX", "false").lower() in {"1","true","yes"}

WEBHOOK_VERIFY   = os.getenv("SENDGRID_WEBHOOK_VERIFY", "false").lower() in {"1","true","yes"}
WEBHOOK_PUBKEY   = os.getenv("SENDGRID_WEBHOOK_PUBLIC_KEY", "").replace("\\n", "\n").strip()

INBOUND_TOKEN    = os.getenv("INBOUND_SHARED_TOKEN", "").strip()

# --- NEW: IMAP settings ---
IMAP_HOST        = os.getenv("IMAP_HOST", "imap.zoho.com").strip()  # Default to Zoho Mail's IMAP server
IMAP_USER        = os.getenv("IMAP_USER", "").strip()
IMAP_PASS        = os.getenv("IMAP_PASS", "").strip()
IMAP_FOLDER      = os.getenv("IMAP_FOLDER", "INBOX").strip()
IMAP_SSL         = os.getenv("IMAP_SSL", "true").lower() in {"1","true","yes"}
IMAP_SINCE_DAYS  = int(os.getenv("IMAP_SINCE_DAYS", "14"))
IMAP_CHECK_TOKEN = os.getenv("IMAP_CHECK_TOKEN", "").strip()
IMAP_MAX_FETCH   = int(os.getenv("IMAP_MAX_FETCH", "300"))  # safety cap
ZOHO_MAIL_CHECK_INTERVAL = int(os.getenv("ZOHO_MAIL_CHECK_INTERVAL", "30"))  # minutes

# ---------------------- DB ----------------------
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        to_email TEXT,
        subject TEXT,
        created_at TEXT,
        provider_msgid TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        msg_id TEXT,
        event TEXT,
        sg_event_id TEXT,
        email TEXT,
        url TEXT,
        reason TEXT,
        timestamp INTEGER,
        payload TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS inbound (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        msg_id TEXT,
        from_email TEXT,
        to_email TEXT,
        subject TEXT,
        timestamp INTEGER,
        snippet TEXT,
        raw_len INTEGER,
        message_id TEXT
    )""")
    
    # Fix for imap_state table - check if it exists with correct schema
    try:
        conn.execute("SELECT id FROM imap_state LIMIT 1")
    except sqlite3.OperationalError:
        # Either table doesn't exist or it has wrong schema
        conn.execute("DROP TABLE IF EXISTS imap_state")
        conn.execute("""CREATE TABLE imap_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_check_ts INTEGER
        )""")
    
    # Ensure columns exist in case of prior schema
    try:
        conn.execute("ALTER TABLE messages ADD COLUMN provider_msgid TEXT")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE inbound ADD COLUMN message_id TEXT")
    except Exception:
        pass
    conn.commit()
    return conn

CONN = init_db()

# ---------------------- UTIL ----------------------
def new_msg_id() -> str:
    return "msg_" + base64.urlsafe_b64encode(os.urandom(9)).decode().rstrip("=")

def insert_message(msg_id: str, to_email: str, subject: str, provider_msgid: str = ""):
    CONN.execute(
        "INSERT OR REPLACE INTO messages (id, to_email, subject, created_at, provider_msgid) VALUES (?,?,?,?,?)",
        (msg_id, to_email, subject, dt.datetime.utcnow().isoformat(), provider_msgid)
    )
    CONN.commit()

def insert_event(msg_id: str, event: str, sg_event_id: str, email: str, url: Optional[str], reason: Optional[str], ts: int, payload: Dict[str, Any]):
    CONN.execute(
        "INSERT INTO events (msg_id, event, sg_event_id, email, url, reason, timestamp, payload) VALUES (?,?,?,?,?,?,?,?)",
        (msg_id, event, sg_event_id, email, url, reason, ts, json.dumps(payload))
    )
    CONN.commit()

def insert_inbound(msg_id: str, from_email: str, to_email: str, subject: str, ts: int, snippet: str, raw_len: int, message_id: str = ""):
    CONN.execute(
        "INSERT INTO inbound (msg_id, from_email, to_email, subject, timestamp, snippet, raw_len, message_id) VALUES (?,?,?,?,?,?,?,?)",
        (msg_id, from_email, to_email, subject, ts, snippet, raw_len, message_id)
    )
    CONN.commit()

def missing_envs() -> List[str]:
    missing = []
    if not SENDGRID_API_KEY: missing.append("SENDGRID_API_KEY")
    if not FROM_EMAIL:       missing.append("SENDGRID_FROM_EMAIL (or FROM_EMAIL)")
    return missing

def verify_event_signature(body: bytes, headers: Dict[str, str]) -> bool:
    if not (WEBHOOK_VERIFY and HAVE_VERIFY and WEBHOOK_PUBKEY):
        return True
    try:
        ew = EventWebhook()
        signature = headers.get(EventWebhookHeader.SIGNATURE)
        timestamp = headers.get(EventWebhookHeader.TIMESTAMP)
        if not signature or not timestamp:
            return False
        pubkey = ew.convert_public_key_to_ecdsa(WEBHOOK_PUBKEY)
        return ew.verify_signature(payload=body, signature=signature, timestamp=timestamp, public_key=pubkey)
    except Exception:
        return False

# --- NEW: helpers for email decoding / matching ---
def _decode_header(value: Optional[str]) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        try:
            if isinstance(text, bytes):
                out.append(text.decode(enc or "utf-8", errors="replace"))
            else:
                out.append(text)
        except Exception:
            out.append(text if isinstance(text, str) else text.decode("utf-8", errors="replace"))
    return "".join(out)

def _strip_html(html: str) -> str:
    # quick & dirty
    return re.sub(r"<[^>]+>", " ", html or "")

def _extract_text(msg: pyemail.message.Message) -> str:
    if msg.is_multipart():
        # Prefer text/plain
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    pass
        # Fallback to text/html
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/html":
                try:
                    html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                    return _strip_html(html)
                except Exception:
                    pass
        return ""
    else:
        payload = msg.get_payload(decode=True)
        if payload is None:
            # sometimes not base64/quoted-printable encoded
            return (msg.get_payload() or "")
        charset = msg.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except Exception:
            return payload.decode("utf-8", errors="replace")

def _parse_date_ts(date_header: Optional[str]) -> int:
    try:
        dt_obj = parsedate_to_datetime(date_header)
        if dt_obj.tzinfo:
            dt_obj = dt_obj.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return int(dt_obj.timestamp())
    except Exception:
        return int(dt.datetime.utcnow().timestamp())

def _sanitize_msgid(mid: Optional[str]) -> str:
    if not mid:
        return ""
    return mid.strip().strip("<>").strip()

TOKEN_RE = re.compile(r"(msg_[A-Za-z0-9_\-]{6,})")

def _find_tracking_token(subject: str, body: str) -> Optional[str]:
    m = TOKEN_RE.search(subject or "")
    if m:
        return m.group(1)
    m = TOKEN_RE.search(body or "")
    if m:
        return m.group(1)
    return None

def _find_msg_by_provider_id(provider_mid: str) -> Optional[str]:
    provider_mid = _sanitize_msgid(provider_mid)
    if not provider_mid:
        return None
    row = CONN.execute("SELECT id FROM messages WHERE provider_msgid = ? LIMIT 1", (provider_mid,)).fetchone()
    if row:
        return row["id"]
    # also try angle-bracket variants just in case
    row = CONN.execute("SELECT id FROM messages WHERE provider_msgid = ? LIMIT 1", ("<%s>" % provider_mid,)).fetchone()
    if row:
        return row["id"]
    return None

def _fallback_match_by_sender(from_addr: str, mail_ts: int) -> Optional[str]:
    # Heuristic: pick the most recent message you sent TO this address before/near this reply time
    row = CONN.execute(
        """
        SELECT id, created_at
        FROM messages
        WHERE lower(to_email)=lower(?)
        ORDER BY datetime(created_at) DESC
        LIMIT 1
        """,
        (from_addr,)
    ).fetchone()
    if row:
        return row["id"]
    return None

# ---------------------- APP ----------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting SendGrid Tracker…")
    # Auto-send emails on startup
    await send_auto_emails()
    yield
    print("Shutting down…")

app = FastAPI(title="SendGrid Tracker", lifespan=lifespan)

# ---------------------- MODELS ----------------------
class SendRequest(BaseModel):
    to: EmailStr
    subject: str
    html: Optional[str] = None
    text: Optional[str] = None
    sandbox: Optional[bool] = None

# ---------------------- ROUTES ----------------------
@app.get("/", response_class=HTMLResponse)
def home():
    warn = ""
    miss = missing_envs()
    if miss:
        warn = f"<p style='color:red'>Missing env vars: {', '.join(miss)}</p>"
    from_line = FROM_EMAIL if not FROM_NAME else f"{FROM_NAME} &lt;{FROM_EMAIL}&gt;"

    imap_warn = ""
    if not (IMAP_HOST and IMAP_USER and IMAP_PASS):
        imap_warn = "<p style='color:#a66'>IMAP not fully configured; set IMAP_USER, IMAP_PASS.</p>"

    zoho_config = """
    <hr>
    <p><b>Zoho Mail Configuration:</b></p>
    <ol>
      <li>Set IMAP_HOST=imap.zoho.com (default)</li>
      <li>Set IMAP_USER=your.email@zohomail.com</li>
      <li>Set IMAP_PASS=your_password or app_specific_password</li>
      <li>Enable IMAP in your Zoho Mail settings (Settings → Mail Accounts → Your Account → IMAP Access)</li>
      <li>For automation, set up a cron job to call <code>/zoho/check?token=YOUR_TOKEN</code> periodically</li>
    </ol>
    """

    return f"""
    <h2>SendGrid Email Tracker</h2>
    {warn}{imap_warn}
    <p><b>From:</b> {from_line}</p>
    <form method="post" action="/send" style="margin-bottom:1rem">
      <p><label>To: <input name="to" type="email" required></label></p>
      <p><label>Subject: <input name="subject" type="text" required></label></p>
      <p><label>Text: <input name="text" type="text" value="Hello! (ref: will include msg_ token)"></label></p>
      <p><label>HTML:</label><br><textarea name="html" rows="5" cols="60">&lt;b&gt;Hello&lt;/b&gt;</textarea></p>
      <p><label>Sandbox? <input name="sandbox" type="checkbox" {"checked" if DEFAULT_SANDBOX else ""}></label></p>
      <button type="submit">Send Email</button>
    </form>
    <p><a href="/dashboard">Dashboard</a> • <a href="/docs">Open API docs</a></p>
    <hr>
    <p><b>Configure in SendGrid:</b></p>
    <ol>
      <li>Settings → Sender Authentication → Verify sender for <code>{FROM_EMAIL or "your email"}</code></li>
      <li>Settings → Event Webhook → POST to <code>{BASE_URL}/events</code> (Delivered, Open, Click, Bounce, Spam, Unsubscribe, Deferred, Processed)</li>
      <li>Settings → Inbound Parse → POST to <code>{BASE_URL}/inbound{("?token="+INBOUND_TOKEN) if INBOUND_TOKEN else ""}</code> to capture replies</li>
    </ol>
    <hr>
    <p><b>Reply Tracking:</b></p>
    <ol>
      <li>IMAP Check: <a href="/imap/check?token={IMAP_CHECK_TOKEN}">Check Now</a> (requires token)</li>
      <li>Zoho Mail Check: <a href="/zoho/check?token={IMAP_CHECK_TOKEN}">Check Zoho Mail</a> (requires token)</li>
    </ol>
    {zoho_config}
    """

@app.post("/send")
async def send_form(
    to: EmailStr = Form(...),
    subject: str = Form(...),
    text: str = Form(""),
    html: str = Form(""),
    sandbox: Optional[bool] = Form(False),
):
    return await send_email(SendRequest(to=to, subject=subject, text=text, html=html, sandbox=sandbox))

@app.post("/api/send")
async def send_email(data: SendRequest):
    miss = missing_envs()
    if miss:
        raise HTTPException(400, detail=f"Missing env vars: {', '.join(miss)}")
    try:
        use_sandbox = DEFAULT_SANDBOX if data.sandbox is None else data.sandbox
        msg_id = new_msg_id()

        # Build the Mail using Personalization (for custom args)
        mail = Mail()
        mail.from_email = Email(FROM_EMAIL, FROM_NAME or None)
        mail.subject = data.subject

        # Optional Reply-To (recommended to set to your IMAP inbox)
        if REPLY_TO_EMAIL:
            mail.reply_to = Email(REPLY_TO_EMAIL)

        p = Personalization()
        p.add_to(Email(str(data.to)))
        p.add_custom_arg(CustomArg("our_msg_id", msg_id))
        mail.add_personalization(p)

        # Include an explicit (human-invisible) token in body for IMAP matching
        token_footer = f"\n\n<!-- tracking:{msg_id} -->\n"
        if data.html:
            mail.add_content(Content("text/html", (data.html or "") + f"\n<!-- tracking:{msg_id} -->"))
        if data.text or not data.html:
            # Always ensure text contains the token too
            mail.add_content(Content("text/plain", (data.text or "Hello!") + token_footer))

        ts = TrackingSettings()
        ts.open_tracking = OpenTracking(enable=True)
        ts.click_tracking = ClickTracking(enable=True, enable_text=True)
        mail.tracking_settings = ts

        if use_sandbox:
            ms = MailSettings()
            ms.sandbox_mode = SandBoxMode(enable=True)
            mail.mail_settings = ms

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        resp = sg.send(mail)

        # Try to capture provider message id (helps with In-Reply-To/References matching)
        provider_msgid = ""
        try:
            # resp.headers may be dict-like; normalize keys
            headers = getattr(resp, "headers", {}) or {}
            headers_lc = {str(k).lower(): str(v) for k, v in headers.items()} if isinstance(headers, dict) else {}
            provider_msgid = headers_lc.get("x-message-id", "") or headers_lc.get("x-message-id".lower(), "")
            provider_msgid = _sanitize_msgid(provider_msgid)
        except Exception:
            provider_msgid = ""

        insert_message(msg_id, str(data.to), data.subject, provider_msgid)
        return {"status": "sent", "code": getattr(resp, "status_code", None), "our_msg_id": msg_id, "provider_msgid": provider_msgid, "sandbox": use_sandbox}
    except Exception as e:
        raise HTTPException(500, detail=f"Send failed: {e}")

@app.post("/events")
async def events(request: Request):
    body = await request.body()
    headers = {k: v for k, v in request.headers.items()}

    # Optional security: verify signature
    if not verify_event_signature(body, headers):
        raise HTTPException(401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body.decode("utf-8"))  # SendGrid posts JSON array
        if isinstance(payload, dict):
            payload = [payload]
        count = 0
        for ev in payload:
            # event types: delivered, open, click, bounce, spamreport, unsubscribe, deferred, processed, dropped, ...
            event = ev.get("event") or ev.get("event_type") or "unknown"
            sg_event_id = ev.get("sg_event_id", "")
            email_addr = ev.get("email", "")
            url = ev.get("url")
            reason = ev.get("reason") or ev.get("response")
            ts = int(ev.get("timestamp") or dt.datetime.utcnow().timestamp())

            # our_msg_id can come flat or inside custom_args
            msg_id = ev.get("our_msg_id")
            if not msg_id:
                ca = ev.get("custom_args") or {}
                if isinstance(ca, dict):
                    msg_id = ca.get("our_msg_id", "unknown")
                elif isinstance(ca, list):
                    msg_id = next((i.get("value") for i in ca if i.get("key") == "our_msg_id"), "unknown")
                else:
                    msg_id = "unknown"

            insert_event(msg_id, event, sg_event_id, email_addr, url, reason, ts, ev)
            count += 1
        return {"ok": True, "count": count}
    except Exception as e:
        raise HTTPException(400, detail=f"Bad event payload: {e}")

@app.post("/inbound")
async def inbound(request: Request, token: Optional[str] = Query(default=None)):
    # Optional shared token check to avoid abuse
    if INBOUND_TOKEN and token != INBOUND_TOKEN:
        raise HTTPException(401, detail="Invalid inbound token")

    body = await request.body()
    raw_len = len(body)

    from_email, to_email, subject, snippet, msg_id, message_id = "", "", "", "", "inbound", ""
    try:
        # Default Inbound Parse posts form-data
        form = await request.form()
        from_email = str(form.get("from", ""))
        to_email = str(form.get("to", ""))
        subject = str(form.get("subject", ""))
        text = form.get("text", "")
        html = form.get("html", "")
        snippet = (text or _strip_html(html) or "")[:500]
        message_id = _sanitize_msgid(str(form.get("message-id", "")))
        # Try to extract our msg_ token from subject/body
        token = _find_tracking_token(subject, text or html or "")
        if token:
            msg_id = token
        # else leave as "inbound" (unmatched) – you can reconcile later
    except Exception:
        pass

    ts = int(dt.datetime.utcnow().timestamp())
    insert_inbound(msg_id, from_email, to_email, subject, ts, snippet, raw_len, message_id)
    insert_event(msg_id, "inbound_reply", "inbound", from_email, None, None, ts, {"snippet": snippet, "raw_len": raw_len, "message_id": message_id})
    return {"ok": True}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    msgs = CONN.execute("SELECT * FROM messages ORDER BY created_at DESC LIMIT 200").fetchall()
    rows = []
    for m in msgs:
        count = CONN.execute("SELECT COUNT(*) FROM events WHERE msg_id=?", (m["id"],)).fetchone()[0]
        rows.append(
            "<tr>"
            f"<td><a href='/status?id={m['id']}'>{m['id']}</a></td>"
            f"<td>{m['to_email']}</td>"
            f"<td>{m['subject']}</td>"
            f"<td>{m['created_at']}</td>"
            f"<td>{count}</td>"
            f"<td>{m['provider_msgid'] or ''}</td>"
            "</tr>"
        )
    return ("<h2>Dashboard</h2>"
            "<table border=1 cellspacing=0 cellpadding=4>"
            "<tr><th>ID</th><th>To</th><th>Subject</th><th>Time (UTC)</th><th>#Events</th><th>Provider Msg-ID</th></tr>"
            + "".join(rows) + "</table>"
            "<p><a href='/'>Home</a></p>")

@app.get("/status", response_class=HTMLResponse)
def status(id: str):
    msg = CONN.execute("SELECT * FROM messages WHERE id=?", (id,)).fetchone()
    if not msg:
        return HTMLResponse(f"<p>No message found for id {id}</p>", status_code=404)
    events = CONN.execute("SELECT * FROM events WHERE msg_id=? ORDER BY timestamp", (id,)).fetchall()
    inbound = CONN.execute("SELECT * FROM inbound WHERE msg_id=? ORDER BY timestamp", (id,)).fetchall()
    def fmt(ts: int) -> str:
        return dt.datetime.utcfromtimestamp(int(ts)).isoformat()
    erows = "".join([f"<tr><td>{fmt(e['timestamp'])}</td><td>{e['event']}</td><td>{e['email']}</td><td>{e['url']}</td><td>{e['reason']}</td></tr>" for e in events])
    irows = "".join([f"<tr><td>{fmt(i['timestamp'])}</td><td>{i['from_email']}</td><td>{i['to_email']}</td><td>{i['subject']}</td><td>{i['snippet']}</td></tr>" for i in inbound])
    return (f"<h2>Status for {id}</h2>"
            f"<p><b>To:</b> {msg['to_email']}<br><b>Subject:</b> {msg['subject']}</p>"
            "<h3>Events</h3>"
            "<table border=1 cellspacing=0 cellpadding=4><tr><th>Time</th><th>Event</th><th>Email</th><th>URL</th><th>Reason</th></tr>"
            f"{erows}</table>"
            "<h3>Inbound (Replies)</h3>"
            "<table border=1 cellspacing=0 cellpadding=4><tr><th>Time</th><th>From</th><th>To</th><th>Subject</th><th>Snippet</th></tr>"
            f"{irows}</table>"
            "<p><a href='/dashboard'>Back</a></p>")

# ---------------------- IMAP CHECK (NEW) ----------------------
def _imap_connect() -> imaplib.IMAP4:
    if not (IMAP_HOST and IMAP_USER and IMAP_PASS):
        raise HTTPException(400, detail="IMAP not configured: set IMAP_HOST, IMAP_USER, IMAP_PASS")
    M = imaplib.IMAP4_SSL(IMAP_HOST) if IMAP_SSL else imaplib.IMAP4(IMAP_HOST)
    typ, _ = M.login(IMAP_USER, IMAP_PASS)
    if typ != "OK":
        try:
            M.logout()
        except Exception:
            pass
        raise HTTPException(401, detail="IMAP login failed")
    typ, _ = M.select(IMAP_FOLDER, readonly=True)
    if typ != "OK":
        try:
            M.logout()
        except Exception:
            pass
    return M

def _imap_search_since(M: imaplib.IMAP4, since_days: int) -> List[bytes]:
    since_date = (dt.datetime.utcnow() - dt.timedelta(days=since_days)).strftime("%d-%b-%Y")
    typ, data = M.uid("SEARCH", None, f'(SINCE "{since_date}")')
    if typ != "OK":
        return []
    uids = data[0].split()
    if IMAP_MAX_FETCH and len(uids) > IMAP_MAX_FETCH:
        uids = uids[-IMAP_MAX_FETCH:]
    return uids

def _imap_fetch_message(M: imaplib.IMAP4, uid: bytes) -> Optional[pyemail.message.Message]:
    typ, data = M.uid("FETCH", uid, "(RFC822)")
    if typ != "OK" or not data or data[0] is None:
        return None
    # data[0] = (b'UID RFC822', bytes)
    raw = data[0][1]
    if not raw:
        return None
    return pyemail.message_from_bytes(raw)

def _match_to_msg_id(subject: str, body: str, in_reply_to: str, references: str, from_addr: str, mail_ts: int) -> Tuple[str, str]:
    """
    Returns (matched_msg_id, strategy) – strategy = 'token' | 'refs' | 'sender' | 'unmatched'
    """
    # 1) Explicit token in subject/body
    token = _find_tracking_token(subject, body)
    if token:
        return token, "token"

    # 2) References / In-Reply-To -> provider_msgid
    for hdr in [in_reply_to, references]:
        if hdr:
            # Could contain multiple IDs; try each
            mids = re.findall(r"<([^>]+)>", hdr) or [hdr]
            for mid in mids:
                m = _find_msg_by_provider_id(mid)
                if m:
                    return m, "refs"

    # 3) Fallback by sender address
    fallback = _fallback_match_by_sender(from_addr, mail_ts)
    if fallback:
        return fallback, "sender"

    return "inbound", "unmatched"

@app.get("/imap/check")
def imap_check(token: Optional[str] = Query(default=None)):
    if IMAP_CHECK_TOKEN and token != IMAP_CHECK_TOKEN:
        raise HTTPException(401, detail="Invalid token")

    M = _imap_connect()
    try:
        uids = _imap_search_since(M, IMAP_SINCE_DAYS)
        scanned = 0
        inserted = 0
        matched = {"token": 0, "refs": 0, "sender": 0, "unmatched": 0}

        for uid in uids:
            msg = _imap_fetch_message(M, uid)
            if not msg:
                continue
            scanned += 1

            subj = _decode_header(msg.get("Subject"))
            from_email = parseaddr(_decode_header(msg.get("From")))[1]
            to_email = parseaddr(_decode_header(msg.get("To")))[1]
            in_reply_to = _decode_header(msg.get("In-Reply-To"))
            references = _decode_header(msg.get("References"))
            message_id = _sanitize_msgid(_decode_header(msg.get("Message-ID")))
            date_ts = _parse_date_ts(msg.get("Date"))
            body_text = _extract_text(msg)
            snippet = (body_text or "")[:500]
            raw_len = len(body_text.encode("utf-8", errors="ignore"))

            msg_id, strategy = _match_to_msg_id(subj, body_text, in_reply_to, references, from_email, date_ts)
            matched[strategy] += 1

            # Check if we already stored this message_id to avoid duplicates
            if message_id:
                existing = CONN.execute("SELECT 1 FROM inbound WHERE message_id = ? LIMIT 1", (message_id,)).fetchone()
                if existing:
                    continue

            insert_inbound(msg_id, from_email, to_email, subj, date_ts, snippet, raw_len, message_id)
            insert_event(msg_id, "imap_reply", "imap", from_email, None, None, date_ts,
                         {"strategy": strategy, "message_id": message_id, "in_reply_to": in_reply_to, "references": references})
            inserted += 1

        # update last_check time
        now_ts = int(dt.datetime.utcnow().timestamp())
        CONN.execute("INSERT OR REPLACE INTO imap_state (id, last_check_ts) VALUES (1, ?)", (now_ts,))
        CONN.commit()

        return {
            "ok": True,
            "scanned": scanned,
            "inserted": inserted,
            "matched": matched,
            "since_days": IMAP_SINCE_DAYS,
            "folder": IMAP_FOLDER
        }
    finally:
        try:
            M.logout()
        except Exception:
            pass

@app.get("/zoho/check")
def zoho_mail_check(token: Optional[str] = Query(default=None)):
    """Dedicated endpoint for checking Zoho Mail replies"""
    if IMAP_CHECK_TOKEN and token != IMAP_CHECK_TOKEN:
        raise HTTPException(401, detail="Invalid token")

    if not IMAP_HOST.endswith("zoho.com"):
        return {"warning": "IMAP_HOST doesn't appear to be a Zoho Mail server. Set IMAP_HOST=imap.zoho.com"}
    
    # Ensure the imap_state table has the correct schema
    try:
        CONN.execute("SELECT id FROM imap_state LIMIT 1")
    except sqlite3.OperationalError:
        # Table exists but is missing the id column, drop and recreate
        CONN.execute("DROP TABLE IF EXISTS imap_state")
        CONN.execute("""CREATE TABLE imap_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_check_ts INTEGER
        )""")
        CONN.commit()
    
    M = _imap_connect()
    try:
        uids = _imap_search_since(M, IMAP_SINCE_DAYS)
        scanned = 0
        inserted = 0
        matched = {"token": 0, "refs": 0, "sender": 0, "unmatched": 0}

        for uid in uids:
            msg = _imap_fetch_message(M, uid)
            if not msg:
                continue
            scanned += 1

            subj = _decode_header(msg.get("Subject"))
            from_email = parseaddr(_decode_header(msg.get("From")))[1]
            to_email = parseaddr(_decode_header(msg.get("To")))[1]
            in_reply_to = _decode_header(msg.get("In-Reply-To"))
            references = _decode_header(msg.get("References"))
            message_id = _sanitize_msgid(_decode_header(msg.get("Message-ID")))
            date_ts = _parse_date_ts(msg.get("Date"))
            body_text = _extract_text(msg)
            snippet = (body_text or "")[:500]
            raw_len = len(body_text.encode("utf-8", errors="ignore"))

            msg_id, strategy = _match_to_msg_id(subj, body_text, in_reply_to, references, from_email, date_ts)
            matched[strategy] += 1

            # Check if we already stored this message_id to avoid duplicates
            if message_id:
                existing = CONN.execute("SELECT 1 FROM inbound WHERE message_id = ? LIMIT 1", (message_id,)).fetchone()
                if existing:
                    continue

            insert_inbound(msg_id, from_email, to_email, subj, date_ts, snippet, raw_len, message_id)
            insert_event(msg_id, "zoho_reply", "zoho", from_email, None, None, date_ts,
                         {"strategy": strategy, "message_id": message_id, "in_reply_to": in_reply_to, "references": references})
            inserted += 1

        # update last_check time
        now_ts = int(dt.datetime.utcnow().timestamp())
        CONN.execute("INSERT OR REPLACE INTO imap_state (id, last_check_ts) VALUES (1, ?)", (now_ts,))
        CONN.commit()

        return {
            "ok": True,
            "zoho_mail": True,
            "scanned": scanned,
            "inserted": inserted,
            "matched": matched,
            "since_days": IMAP_SINCE_DAYS,
            "folder": IMAP_FOLDER
        }
    finally:
        try:
            M.logout()
        except Exception:
            pass

# ---------------------- AUTO EMAIL SENDING ----------------------
def read_email_template() -> List[Dict[str, Any]]:
    """Read email template file and return list of email configurations"""
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "email_template.json")
    if not os.path.exists(template_path):
        print(f"Warning: email_template.json not found at {template_path}")
        return []
        
    try:
        with open(template_path, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            # Single email template
            return [data]
        elif isinstance(data, list):
            # Multiple email templates
            return data
        else:
            print(f"Warning: Invalid email_template.json format. Expected dict or list, got {type(data)}")
            return []
    except Exception as e:
        print(f"Error reading email_template.json: {e}")
        return []

async def send_auto_emails():
    """Send emails automatically based on template file"""
    templates = read_email_template()
    if not templates:
        print("No email templates found. Skipping auto-send.")
        return
    
    miss = missing_envs()
    if miss:
        print(f"Missing environment variables: {', '.join(miss)}. Cannot send automatic emails.")
        return
    
    sent_count = 0
    for template in templates:
        try:
            to_email = template.get("to")
            subject = template.get("subject")
            html_content = template.get("html")
            text_content = template.get("text", "")
            sandbox = template.get("sandbox", DEFAULT_SANDBOX)
            
            if not to_email or not subject:
                print(f"Skipping template - missing required fields (to, subject): {template}")
                continue
                
            request = SendRequest(
                to=to_email,
                subject=subject,
                html=html_content,
                text=text_content,
                sandbox=sandbox
            )
            
            result = await send_email(request)
            print(f"Auto-sent email to {to_email}: {result}")
            sent_count += 1
            
        except Exception as e:
            print(f"Error sending automatic email: {e}")
    
    print(f"Auto-send complete: {sent_count} emails sent")
