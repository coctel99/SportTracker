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
  reps INTEGER NOT NULL CHECK (reps >= 0),
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
    """Add any missing columns to existing tables (idempotent)."""
    conn = get_db()
    existing = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    migrations = [
        ("name", "ALTER TABLE users ADD COLUMN name TEXT"),
        ("date_of_birth", "ALTER TABLE users ADD COLUMN date_of_birth TEXT"),
        (
            "sex",
            "ALTER TABLE users ADD COLUMN sex TEXT CHECK (sex IN ('male', 'female'))",
        ),
        ("weight", "ALTER TABLE users ADD COLUMN weight REAL"),
    ]
    for col, sql in migrations:
        if col not in existing:
            conn.execute(sql)
    conn.commit()


def init_app(app):
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Database initialized.")
