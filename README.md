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
  - `routes.py` - all HTTP routes (auth, dashboard, exercises, sessions, progress, profile)
  - `auth/` - blueprint, login guard, CSRF hooks, validators, service layer
  - `templates/` - Jinja2 HTML templates
  - `tracker/` - query modules per feature (dashboard, exercises, sessions, progress)
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

## Terraform / Deploy

Infrastructure is managed with Terraform (GCP) and deployed via three GitHub Actions workflows.

### GitHub Actions — Repository Secrets

| Secret | Description |
|---|---|
| `GCP_SA_KEY` | GCP service account key JSON used by Terraform to authenticate |
| `SSH_PRIVATE_KEY` | Private SSH key used by CD to connect to the VM |
| `TF_VAR_APP_SECRET_KEY` | Value written to the server `.env` as `SPORT_TRACKER_SECRET_KEY` |

### GitHub Actions — Repository Variables

| Variable | Description |
|---|---|
| `SSH_HOST` | Public IP address of the VM |
| `SSH_USER` | Linux user on the VM |
| `SSH_PORT` | SSH port (defaults to `22` if not set) |
| `APP_DIR` | Absolute path on the VM where the app is deployed |
| `TF_VAR_PROJECT_ID` | GCP project ID |
| `TF_VAR_GITHUB_REPO` | GitHub repo HTTPS URL cloned onto the VM on first boot |
| `TF_VAR_SSH_PUBLIC_KEY` | Personal public SSH key for direct VM access |
| `TF_VAR_DEPLOY_PUBLIC_KEY` | Public SSH key pair for `SSH_PRIVATE_KEY`, injected into the VM for CD |

### Workflows

**`ci.yml`** — Runs on every push and pull request to any branch. Installs dependencies, runs `ruff` lint and format checks, then runs the full `pytest` suite.

**`cd.yml`** — Runs automatically after CI passes on `main`. SSHs into the VM, pulls the latest code, rebuilds the Docker image, restarts the container with `docker compose up -d --build`, and prunes dangling images.

**`terraform.yml`** — Runs on pushes and pull requests to `main` that touch `terraform/**`, and can also be triggered manually. On a pull request it authenticates to GCP and runs `plan` only. On a push to `main` (or manual trigger) it also runs `apply`, provisioning or updating the VM, firewall rules, and static IP.

## Development Config

- `SPORT_TRACKER_DEBUG` (`true`/`false`, default: `true`)
- `SPORT_TRACKER_HOST` (default: `127.0.0.1`)
- `SPORT_TRACKER_PORT` (default: `5000`)
- `SPORT_TRACKER_SECRET_KEY` (default: `dev` for local only)
- `SPORT_TRACKER_DATABASE` (default: `instance/sport_tracker.sqlite`)

When `SPORT_TRACKER_DEBUG=false`, `SPORT_TRACKER_SECRET_KEY` must be set to a non-default value and `SESSION_COOKIE_SECURE` is automatically enabled.

