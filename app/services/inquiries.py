"""Private, persistent inquiry inbox; no dependencies on the production TDM DB."""
import hashlib
import hmac
import json
import secrets
import smtplib
import sqlite3
import ssl
import time
from contextlib import contextmanager
from email.message import EmailMessage

from app.config import settings
from app.site_config import site_settings

RETENTION_DAYS = 180


@contextmanager
def connection():
    path = site_settings.site_store
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(path, timeout=10)
    path.chmod(0o600)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('''CREATE TABLE IF NOT EXISTS inquiries (
            id TEXT PRIMARY KEY, created REAL NOT NULL, name TEXT NOT NULL,
            email TEXT NOT NULL, data TEXT NOT NULL, service TEXT NOT NULL,
            timeline TEXT NOT NULL, budget TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new', mail TEXT NOT NULL DEFAULT 'pending',
            nonce TEXT UNIQUE NOT NULL)''')
        db.execute('''CREATE TABLE IF NOT EXISTS attempts (
            bucket TEXT NOT NULL, created REAL NOT NULL)''')
        db.execute('CREATE INDEX IF NOT EXISTS attempts_lookup ON attempts(bucket, created)')
        db.execute('DELETE FROM attempts WHERE created < ?', (time.time() - 86400,))
        db.execute('DELETE FROM inquiries WHERE created < ?', (time.time() - RETENTION_DAYS * 86400,))
        db.commit()
        yield db
        db.commit()
    finally:
        db.close()


def rate_limit(ip: str, kind: str, limit: int, seconds: int) -> bool:
    bucket = hmac.new(settings.secret_key.encode(), f'{kind}:{ip}'.encode(), hashlib.sha256).hexdigest()
    now = time.time()
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        count = db.execute('SELECT count(*) FROM attempts WHERE bucket=? AND created>?',
                           (bucket, now - seconds)).fetchone()[0]
        if count >= limit:
            return False
        db.execute('INSERT INTO attempts VALUES (?, ?)', (bucket, now))
        return True


def create_inquiry(body: dict) -> tuple[str, bool]:
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT id FROM inquiries WHERE nonce=?', (body['nonce'],)).fetchone()
        if old:
            return old['id'], False
        reference = 'SR-' + secrets.token_hex(6).upper()
        values = [reference, time.time()] + [body[k] for k in ('name', 'email', 'data', 'service', 'timeline', 'budget')]
        db.execute('''INSERT INTO inquiries
            (id,created,name,email,data,service,timeline,budget,nonce)
            VALUES (?,?,?,?,?,?,?,?,?)''', (*values, body['nonce']))
        return reference, True


def notify(reference: str):
    # Store first; SMTP failure can never discard a valid inquiry.
    with connection() as db:
        row = db.execute('SELECT * FROM inquiries WHERE id=?', (reference,)).fetchone()
    if not row:
        return
    state = 'not_configured'
    if all((site_settings.smtp_host, site_settings.smtp_user,
            site_settings.smtp_password, site_settings.inquiry_to)):
        message = EmailMessage()
        message['Subject'] = f'[새롱 개발 문의] {reference}'
        message['From'] = site_settings.smtp_from or site_settings.smtp_user
        message['To'] = site_settings.inquiry_to
        message['Reply-To'] = row['email']
        message.set_content('\n\n'.join(f'{key}: {row[key]}' for key in
                            ('name', 'email', 'data', 'service', 'timeline', 'budget')))
        try:
            cls = smtplib.SMTP_SSL if site_settings.smtp_ssl else smtplib.SMTP
            kwargs = {'timeout': 15}
            if site_settings.smtp_ssl:
                kwargs['context'] = ssl.create_default_context()
            with cls(site_settings.smtp_host, site_settings.smtp_port, **kwargs) as smtp:
                if not site_settings.smtp_ssl:
                    smtp.starttls(context=ssl.create_default_context())
                smtp.login(site_settings.smtp_user, site_settings.smtp_password)
                smtp.send_message(message)
            state = 'sent'
        except Exception:
            state = 'failed'  # Do not log credentials, recipient addresses or inquiry bodies.
    with connection() as db:
        db.execute('UPDATE inquiries SET mail=? WHERE id=?', (state, reference))


def list_inquiries(page: int = 1):
    with connection() as db:
        total = db.execute('SELECT count(*) FROM inquiries').fetchone()[0]
        rows = db.execute('SELECT * FROM inquiries ORDER BY created DESC LIMIT 20 OFFSET ?',
                          ((page - 1) * 20,)).fetchall()
    return [dict(row) for row in rows], total


def update_inquiry(reference: str, status: str):
    with connection() as db:
        if status == 'delete':
            return db.execute('DELETE FROM inquiries WHERE id=?', (reference,)).rowcount
        return db.execute('UPDATE inquiries SET status=? WHERE id=?', (status, reference)).rowcount
