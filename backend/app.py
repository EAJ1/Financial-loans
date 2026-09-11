"""Bloom's saved-plan API. No identity, contact or banking data is collected."""
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from wsgiref.simple_server import make_server

ROOT = Path(__file__).resolve().parent.parent
DATABASE = Path(os.environ.get('BLOOM_DATABASE', str(ROOT / 'data' / 'bloom.sqlite3')))
ALLOWED_ORIGIN = os.environ.get('BLOOM_ALLOWED_ORIGIN', 'https://eaj1.github.io')
STATIC = {'/': 'index.html', '/index.html': 'index.html', '/styles.css': 'styles.css',
          '/script.js': 'script.js', '/config.js': 'config.js', '/plans.js': 'plans.js'}
PURPOSES = {'everyday', 'home', 'milestone', 'other'}


@contextmanager
def connect():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('''CREATE TABLE IF NOT EXISTS plans (
        reference TEXT PRIMARY KEY, amount INTEGER NOT NULL CHECK(amount BETWEEN 500 AND 25000),
        months INTEGER NOT NULL CHECK(months BETWEEN 3 AND 24), purpose TEXT NOT NULL,
        annual_rate REAL NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL)''')
    schema = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='plans'").fetchone()[0]
    if 'BETWEEN 1000 AND 25000' in schema:
        with db:
            db.execute('ALTER TABLE plans RENAME TO plans_previous')
            db.execute(schema.replace('BETWEEN 1000 AND 25000', 'BETWEEN 500 AND 25000'))
            db.execute('INSERT INTO plans SELECT * FROM plans_previous')
            db.execute('DROP TABLE plans_previous')
    db.execute('CREATE INDEX IF NOT EXISTS plans_expiry ON plans(expires_at)')
    try:
        with db:
            yield db
    finally:
        db.close()


def now():
    return datetime.now(timezone.utc)


def validate(payload):
    if not isinstance(payload, dict) or set(payload) != {'amount', 'months', 'purpose'}:
        raise ValueError('Provide only amount, months and purpose.')
    amount, months, purpose = payload['amount'], payload['months'], payload['purpose']
    if type(amount) is not int or not 500 <= amount <= 25000 or amount % 500:
        raise ValueError('Choose an amount from R 500 to R 25,000 in steps of R 500.')
    if type(months) is not int or months not in range(3, 25, 3):
        raise ValueError('Choose a term from 3 to 24 months in steps of 3.')
    if not isinstance(purpose, str) or purpose not in PURPOSES:
        raise ValueError('Choose a listed loan purpose.')
    return amount, months, purpose


def application(environ, start_response):
    method = environ.get('REQUEST_METHOD', 'GET')
    path = environ.get('PATH_INFO', '/')
    origin = environ.get('HTTP_ORIGIN', '')
    headers = [('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'),
               ('Referrer-Policy', 'no-referrer')]
    if origin == ALLOWED_ORIGIN:
        headers += [('Access-Control-Allow-Origin', origin), ('Vary', 'Origin')]

    def respond(status, payload):
        data = json.dumps(payload).encode()
        start_response(status, headers + [('Content-Type', 'application/json'), ('Content-Length', str(len(data)))])
        return [data]

    if method == 'OPTIONS' and path.startswith('/api/'):
        headers.extend([('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
                        ('Access-Control-Allow-Headers', 'Content-Type')])
        return respond('200 OK', {})
    if path in STATIC and method == 'GET':
        filename = STATIC[path]
        content = (ROOT / filename).read_bytes()
        content_type = 'text/html' if filename.endswith('.html') else 'text/css' if filename.endswith('.css') else 'text/javascript'
        start_response('200 OK', headers + [('Content-Type', content_type + '; charset=utf-8')])
        return [content]
    try:
        if path == '/api/health' and method == 'GET':
            with connect() as db:
                db.execute('SELECT 1')
            return respond('200 OK', {'service': 'bloom-plans', 'available': True})
        if path == '/api/plans' and method == 'POST':
            if environ.get('CONTENT_TYPE', '').split(';')[0] != 'application/json':
                return respond('415 Unsupported Media Type', {'error': 'Send JSON data.'})
            try:
                size = int(environ.get('CONTENT_LENGTH') or '0')
            except ValueError:
                return respond('400 Bad Request', {'error': 'Invalid content length.'})
            if not 0 < size <= 1024:
                return respond('413 Payload Too Large', {'error': 'Request must be between 1 and 1,024 bytes.'})
            try:
                amount, months, purpose = validate(json.loads(environ['wsgi.input'].read(size)))
            except (ValueError, UnicodeDecodeError):
                return respond('400 Bad Request', {'error': 'Check your amount, term and loan purpose.'})
            created = now()
            reference = secrets.token_hex(16)
            expires = (created + timedelta(days=30)).isoformat()
            with connect() as db:
                db.execute('DELETE FROM plans WHERE expires_at <= ?', (created.isoformat(),))
                # A hard storage cap protects this small prototype from unbounded writes.
                if db.execute('SELECT count(*) FROM plans').fetchone()[0] >= 10000:
                    return respond('503 Service Unavailable', {'error': 'Plan storage is full. Please try again later.'})
                db.execute('INSERT INTO plans VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (reference, amount, months, purpose, 0.40, created.isoformat(), expires))
            return respond('201 Created', {'reference': reference, 'expires_at': expires})
        if path.startswith('/api/plans/') and method == 'GET':
            reference = path.removeprefix('/api/plans/')
            if not re.fullmatch('[a-f0-9]{32}', reference):
                return respond('404 Not Found', {'error': 'Plan not found. Check the reference; plans expire after 30 days.'})
            with connect() as db:
                row = db.execute('SELECT * FROM plans WHERE reference = ? AND expires_at > ?',
                                 (reference, now().isoformat())).fetchone()
            if row:
                return respond('200 OK', dict(row))
            return respond('404 Not Found', {'error': 'Plan not found. Check the reference; plans expire after 30 days.'})
        return respond('404 Not Found', {'error': 'Not found.'})
    except sqlite3.Error:
        return respond('503 Service Unavailable', {'error': 'Plan storage is temporarily unavailable.'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8001'))
    with make_server('127.0.0.1', port, application) as server:
        print(f'Bloom Finance: http://localhost:{port}', flush=True)
        server.serve_forever()
