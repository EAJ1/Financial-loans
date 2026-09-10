# Bloom Finance

A responsive loans website concept with a repayment calculator, monthly budget check and SQLite-backed saved plans. No loans are issued or applications submitted.

## Run locally

Requires Python 3.10+ with SQLite. No additional packages are needed locally.

```sh
python3 backend/app.py
```

Open http://localhost:8001. The database is created at `data/bloom.sqlite3` on first use and excluded from Git. Use this server rather than a generic static server, which cannot run the API and may expose project files.

## Features

- Illustrative monthly repayments using 24% annual interest, excluding fees.
- Budget check using income and expenses. These figures stay in the browser and are never saved or sent.
- Save amount, term and purpose for 30 days. Reopen a plan with its random 32-character reference.
- No contact, identity or banking data is collected. Anyone with a reference can view that plan; references are not customer authentication.
- Save and restore buttons are disabled when the backend is unavailable. No fake successful saves or local-storage database fallback.

## Connect the live GitHub Pages site

GitHub Pages cannot execute the Python backend. Deploy it to a Python host with a persistent disk and HTTPS, then set the public backend URL in `config.js` (without `/api`). Never add secrets to that file.

```sh
python3 -m pip install -r backend/requirements.txt
gunicorn --bind 0.0.0.0:8001 backend.app:application
```

Set `BLOOM_DATABASE` to an absolute file path on the persistent disk, and `BLOOM_ALLOWED_ORIGIN=https://eaj1.github.io`. The host must provide HTTPS and proxy traffic to the server. Push the configured frontend to GitHub once the backend is ready. The budget check works on GitHub Pages without a backend.

The local server binds only to loopback. Public files are served from an explicit whitelist; database and repository files cannot be downloaded. SQL uses parameter binding and values are validated server-side. References expire after 30 days; expired rows are deleted on the next save. Schedule periodic cleanup if a strict physical deletion schedule is required. There is a 10,000-plan storage cap; add host-level rate limiting and backups before public use. This prototype does not include applicant accounts, admin access, approvals or document uploads.

## API

- `GET /api/health`: service/database availability.
- `POST /api/plans`: JSON with only `amount` (1000–25000 in steps of 500), `months` (3–24 in steps of 3), and `purpose` (`everyday`, `home`, `milestone`, `other`). Returns reference and expiry.
- `GET /api/plans/{reference}`: non-expired plan. No public listing exists.

## Checks

```sh
python3 -m unittest discover -s tests -v
node --check script.js
node --check plans.js
```

Bloom Finance is a placeholder brand. Content and rates are examples, not lender quotes.
