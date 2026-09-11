import io
import json
from pathlib import Path
import tempfile
import unittest
from backend import app

class SavedPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original = app.DATABASE
        app.DATABASE = Path(self.temp.name) / 'plans.sqlite3'

    def tearDown(self):
        app.DATABASE = self.original
        self.temp.cleanup()

    def request(self, path, method='GET', payload=None, origin=''):
        raw = json.dumps(payload).encode() if payload is not None else b''
        result = {}
        def start(status, headers):
            result.update(status=int(status.split()[0]), headers=dict(headers))
        content = b''.join(app.application({'PATH_INFO': path, 'REQUEST_METHOD': method,
            'CONTENT_TYPE': 'application/json', 'CONTENT_LENGTH': str(len(raw)),
            'wsgi.input': io.BytesIO(raw), 'HTTP_ORIGIN': origin}, start))
        return result, json.loads(content)

    def create(self):
        return self.request('/api/plans', 'POST', {'amount': 5000, 'months': 6, 'purpose': 'home'})

    def test_save_and_retrieve_persisted_plan(self):
        result, saved = self.create()
        self.assertEqual(result['status'], 201)
        self.assertTrue(app.DATABASE.exists())
        result, loaded = self.request('/api/plans/' + saved['reference'])
        self.assertEqual(result['status'], 200)
        self.assertEqual((loaded['amount'], loaded['months'], loaded['purpose']), (5000, 6, 'home'))
        self.assertEqual(len(saved['reference']), 32)

    def test_r500_plan_and_existing_database_migration(self):
        _, existing = self.create()
        with app.connect() as db:
            schema = db.execute("SELECT sql FROM sqlite_master WHERE name='plans'").fetchone()[0]
            db.execute('ALTER TABLE plans RENAME TO temporary_plans')
            db.execute(schema.replace('BETWEEN 500 AND 25000', 'BETWEEN 1000 AND 25000'))
            db.execute('INSERT INTO plans SELECT * FROM temporary_plans')
            db.execute('DROP TABLE temporary_plans')
        result, saved = self.request('/api/plans', 'POST',
                                     {'amount': 500, 'months': 6, 'purpose': 'everyday'})
        self.assertEqual(result['status'], 201)
        result, loaded = self.request('/api/plans/' + saved['reference'])
        self.assertEqual(loaded['amount'], 500)
        result, loaded = self.request('/api/plans/' + existing['reference'])
        self.assertEqual(result['status'], 200)
        self.assertEqual(loaded['amount'], 5000)

    def test_invalid_values_are_rejected(self):
        for payload in [[], {'amount': True, 'months': 6, 'purpose': 'home'},
            {'amount': 999, 'months': 6, 'purpose': 'home'},
            {'amount': 5000, 'months': 5, 'purpose': 'home'},
            {'amount': 5000, 'months': 6, 'purpose': "'; DROP TABLE plans;--"},
            {'amount': 5000, 'months': 6, 'purpose': 'home', 'email': 'not-collected@example.com'}]:
            with self.subTest(payload=payload):
                result, _ = self.request('/api/plans', 'POST', payload)
                self.assertEqual(result['status'], 400)

    def test_expired_plan_is_not_retrievable(self):
        _, saved = self.create()
        with app.connect() as db:
            db.execute("UPDATE plans SET expires_at='2000-01-01'")
        result, _ = self.request('/api/plans/' + saved['reference'])
        self.assertEqual(result['status'], 404)

    def test_no_public_listing_or_database_download(self):
        self.create()
        for path in ['/api/plans', '/data/bloom.sqlite3', '/backend/app.py', '/.git/config', '/../../data/bloom.sqlite3']:
            result, _ = self.request(path)
            self.assertEqual(result['status'], 404)

    def test_cors_is_limited_to_configured_origin(self):
        result, _ = self.request('/api/health', origin=app.ALLOWED_ORIGIN)
        self.assertEqual(result['headers']['Access-Control-Allow-Origin'], app.ALLOWED_ORIGIN)
        result, _ = self.request('/api/health', origin='https://example.org')
        self.assertNotIn('Access-Control-Allow-Origin', result['headers'])

    def test_bad_reference_is_not_found(self):
        result, _ = self.request('/api/plans/not-a-reference')
        self.assertEqual(result['status'], 404)

if __name__ == '__main__':
    unittest.main()
