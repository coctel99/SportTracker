"""SQLite connection utilities and schema initialization for the app."""

import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  name TEXT,
  date_of_birth TEXT,
  sex TEXT CHECK (sex IN ('male', 'female')),
  weight REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS exercises (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  default_sets INTEGER,
  default_reps INTEGER,
  default_duration_seconds INTEGER CHECK (default_duration_seconds > 0),
  default_duration_unit TEXT CHECK (default_duration_unit IN ('seconds', 'minutes', 'hours')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, name),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  session_date TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS session_exercises (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL,
  exercise_id INTEGER NOT NULL,
  position INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
  FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS exercise_sets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_exercise_id INTEGER NOT NULL,
  set_number INTEGER NOT NULL,
  reps INTEGER CHECK (reps >= 0),
  duration_seconds INTEGER CHECK (duration_seconds > 0),
  FOREIGN KEY (session_exercise_id) REFERENCES session_exercises(id) ON DELETE CASCADE
);
"""


def get_db():
    if "db" not in g:
        database_path = Path(current_app.config["DATABASE"])
        database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
    return g.db


def close_db(_=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def migrate_db():
    """Add any missing columns to existing tables and fix constraints (idempotent)."""
    conn = get_db()

    existing_users = {
        row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    user_migrations = [
        ("name", "ALTER TABLE users ADD COLUMN name TEXT"),
        ("date_of_birth", "ALTER TABLE users ADD COLUMN date_of_birth TEXT"),
        (
            "sex",
            "ALTER TABLE users ADD COLUMN sex TEXT CHECK (sex IN ('male', 'female'))",
        ),
        ("weight", "ALTER TABLE users ADD COLUMN weight REAL"),
    ]
    for col, sql in user_migrations:
        if col not in existing_users:
            conn.execute(sql)

    existing_exercises = {
        row[1] for row in conn.execute("PRAGMA table_info(exercises)").fetchall()
    }
    exercises_migrations = [
        (
            "default_duration_seconds",
            "ALTER TABLE exercises ADD COLUMN default_duration_seconds INTEGER CHECK (default_duration_seconds > 0)",
        ),
        (
            "default_duration_unit",
            "ALTER TABLE exercises ADD COLUMN default_duration_unit TEXT CHECK (default_duration_unit IN ('seconds', 'minutes', 'hours'))",
        ),
    ]
    for col, sql in exercises_migrations:
        if col not in existing_exercises:
            conn.execute(sql)

    sets_cols = {
        row[1]: row
        for row in conn.execute("PRAGMA table_info(exercise_sets)").fetchall()
    }

    if "duration_seconds" not in sets_cols:
        conn.execute(
            "ALTER TABLE exercise_sets ADD COLUMN duration_seconds INTEGER CHECK (duration_seconds > 0)"
        )
        sets_cols = {
            row[1]: row
            for row in conn.execute("PRAGMA table_info(exercise_sets)").fetchall()
        }

    reps_col = sets_cols.get("reps")
    if reps_col and reps_col[3] == 1:  # notnull == 1
        conn.executescript("""
            PRAGMA foreign_keys = OFF;

            CREATE TABLE exercise_sets_new (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_exercise_id INTEGER NOT NULL,
              set_number INTEGER NOT NULL,
              reps INTEGER CHECK (reps >= 0),
              duration_seconds INTEGER CHECK (duration_seconds > 0),
              FOREIGN KEY (session_exercise_id) REFERENCES session_exercises(id) ON DELETE CASCADE
            );

            INSERT INTO exercise_sets_new (id, session_exercise_id, set_number, reps, duration_seconds)
            SELECT id, session_exercise_id, set_number, reps,
                   CASE WHEN typeof(duration_seconds) != 'null' THEN duration_seconds ELSE NULL END
            FROM exercise_sets;

            DROP TABLE exercise_sets;
            ALTER TABLE exercise_sets_new RENAME TO exercise_sets;

            PRAGMA foreign_keys = ON;
        """)

    conn.commit()


def init_app(app):
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Database initialized.")

    @app.cli.command("migrate-db")
    def migrate_db_command():
        """Apply any pending schema migrations to an existing database."""
        migrate_db()
        print("Database migrated.")
