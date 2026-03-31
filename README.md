# Sport Tracker MVP

Minimal Flask + SQLite app to track personal training sessions with exercises, sets, and reps.

## Features

- User registration and login
- User-scoped exercises with default sets/reps
- Session logger with reps per set (`12,10,8` format)
- Progress pages with per-exercise line chart (daily reps and sets)
- SQLite schema designed for future extension (e.g., exercise descriptions)
- Frontend: Tailwind CSS (CDN), Chart.js, vanilla JS

## Project Structure

- `main.py` - app entrypoint
- `app/` - Flask app package
  - `__init__.py` - app factory
  - `db.py` - SQLite connection and schema init
  - `auth.py` - auth routes and login guard
  - `routes.py` - dashboard, exercises, sessions, progress routes
  - `templates/` - simple HTML UI
- `tests/` - pytest tests for auth, exercises, sessions/progress

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Optional: update values in .env and export before running
# export $(grep -v '^#' .env | xargs)
python main.py
```

Open: http://127.0.0.1:5000

## Run Tests

```bash
pytest -q
```

## Development Config

- `SPORT_TRACKER_DEBUG` (`true`/`false`, default: `true`)
- `SPORT_TRACKER_HOST` (default: `127.0.0.1`)
- `SPORT_TRACKER_PORT` (default: `5000`)
- `SPORT_TRACKER_SECRET_KEY` (default: `dev` for local only)
- `SPORT_TRACKER_DATABASE` (default: `instance/sport_tracker.sqlite`)

When `SPORT_TRACKER_DEBUG=false`, `SPORT_TRACKER_SECRET_KEY` must be set to a non-default value.

