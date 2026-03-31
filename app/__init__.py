"""Application factory and environment-based Flask configuration."""

import os
from pathlib import Path

from flask import Flask

from app import db


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def create_app(test_config=None):
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="frontend",
        static_url_path="/static",
    )
    default_database = str(Path(app.instance_path) / "sport_tracker.sqlite")
    debug_mode = _env_bool("SPORT_TRACKER_DEBUG", True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SPORT_TRACKER_SECRET_KEY", "dev"),
        DATABASE=os.getenv("SPORT_TRACKER_DATABASE", default_database),
        DEBUG=debug_mode,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config is not None:
        app.config.update(test_config)

    if not app.config.get("DEBUG") and not app.config.get("TESTING"):
        if app.config.get("SECRET_KEY") == "dev":
            raise RuntimeError(
                "SPORT_TRACKER_SECRET_KEY must be set when DEBUG is disabled."
            )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    from app.auth import bp as auth_bp
    from app.routes import bp as routes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(routes_bp)

    return app
