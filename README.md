# Training Awareness Demo Dashboard

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Framework](https://img.shields.io/badge/Framework-Flask-black)
![Database](https://img.shields.io/badge/Database-SQLite-green)
![Mode](https://img.shields.io/badge/Mode-Safe%20Demo-orange)

## Overview

This project is a safe cybersecurity awareness demo built with Flask.

It keeps the original two-step page flow and dashboard style, but it does not store typed email values, second-step input, passwords, real user tracking data, or live geolocation data. The dashboard is powered entirely by synthetic training records.

## Safe Behavior

- The public pages still render and submit normally.
- Typed values from the public pages are ignored after validation.
- The app generates synthetic demo sessions for awareness training analytics.
- Dashboard records are labeled as training/demo data.
- API responses never expose any field named `password`.

## Features

- Google-style two-step training flow
- Synthetic training session generation
- SQLite-backed mock analytics
- Dashboard statistics cards
- Session filters
- Chart.js charts
- Audit log feed
- Mobile-responsive dashboard

## Project Structure

```text
project/
|-- app.py
|-- requirements.txt
|-- README.md
`-- templates/
    |-- login_email.html
    |-- login_password.html
    `-- results.html
```

## Run Locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the app:

```bash
python app.py
```

3. Open:

- Public flow: `http://127.0.0.1:5000/`
- Dashboard: `http://127.0.0.1:5000/results`

## API Endpoints

### `GET /api/stats`

Returns aggregate demo analytics:

- `total_sessions`
- `today_sessions`
- `week_sessions`
- `mobile_count`
- `desktop_count`
- `top_browsers`
- `top_operating_systems`
- `top_countries`
- `visitors_per_day`

### `GET /api/data`

Returns synthetic demo session rows. Supports optional filters:

- `search`
- `ip`
- `device`
- `country`
- `date`

### `GET /api/audit-logs`

Returns recent dashboard and API activity logs for the demo.

## Notes

- The app uses `/tmp/database.db` so it can run in environments like Vercel.
- Existing legacy tables are preserved for compatibility.
- The synthetic dashboard data is seeded automatically on first run.

## License

Educational and research use only.
