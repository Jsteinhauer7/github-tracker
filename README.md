# GitHub Trend Tracker

A data pipeline that automatically fetches trending GitHub repositories every hour using APScheduler, stores them in a database, and visualizes the data in a Matrix-inspired dashboard.

## Features

- **Automated pipeline** — APScheduler fetches trending repos every hour with no user interaction required
- **GitHub Search API** — pulls the top 50 most-starred repos created in the last 30 days
- **Star & fork tracking** — updates existing repos on each fetch to track growth over time
- **Fetch log** — every run is logged with how many repos were added or updated
- **Language breakdown** — doughnut chart showing language distribution across tracked repos
- **Top repos chart** — horizontal bar chart of the highest-starred repos
- **Search & filter** — filter by language or search by name/description
- **Matrix UI** — falling katakana/Latin characters, glass panels, neon green terminal aesthetic

## Tech Stack

- Python 3 / Flask
- APScheduler for background job scheduling
- SQLite via Flask-SQLAlchemy (PostgreSQL in production)
- GitHub Search API (free, no key required)
- Chart.js for data visualization
- Deployed on Render

## How the Pipeline Works

1. On startup, APScheduler registers a job to run `fetch_trending()` every hour
2. `fetch_trending()` queries the GitHub Search API for repos created in the last 30 days sorted by stars
3. New repos are inserted; existing repos have their star/fork counts updated
4. Every run is recorded in the `FetchLog` table with a timestamp and result summary
5. The dashboard reads from the database and renders charts + repo list in real time

## Getting Started

### 1. Install dependencies

```bash
pip install flask flask-sqlalchemy apscheduler requests
```

### 2. Run the app

```bash
python app.py
```

### 3. Open in browser

```
http://127.0.0.1:5000
```

Click **FETCH_NOW** to trigger an immediate fetch, or wait for the hourly scheduler to run automatically.

### Optional: GitHub Token

To increase the API rate limit from 60 to 5000 requests/hour, add a `GITHUB_TOKEN` environment variable with a personal access token from github.com/settings/tokens.

## Project Structure

```
GitHub_Tracker/
├── app.py               # Flask app, pipeline logic, APScheduler setup, database models
├── Procfile             # Gunicorn config for deployment
├── requirements.txt     # Python dependencies
└── templates/
    └── index.html       # Matrix-themed dashboard with charts and repo table
```
