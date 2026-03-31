#!/bin/sh
set -e

# Initialise (or migrate) the SQLite schema before starting the server.
python - <<'EOF'
from app import create_app
from app.db import init_db
app = create_app()
with app.app_context():
    init_db()
EOF

exec "$@"

