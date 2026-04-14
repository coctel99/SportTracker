import os

from app import create_app
from app.db import init_db, migrate_db

app = create_app()

with app.app_context():
    init_db()
    migrate_db()


if __name__ == "__main__":
    app.run(
        host=os.getenv("SPORT_TRACKER_HOST", "127.0.0.1"),
        port=int(os.getenv("SPORT_TRACKER_PORT", "5000")),
        debug=app.config["DEBUG"],
    )
