import pytest

from app import create_app


def test_create_app_reads_env(monkeypatch, tmp_path):
    db_path = tmp_path / "env_test.sqlite"
    monkeypatch.setenv("SPORT_TRACKER_DATABASE", str(db_path))
    monkeypatch.setenv("SPORT_TRACKER_SECRET_KEY", "local-secret")
    monkeypatch.setenv("SPORT_TRACKER_DEBUG", "false")

    app = create_app({"TESTING": True})

    assert app.config["DATABASE"] == str(db_path)
    assert app.config["SECRET_KEY"] == "local-secret"
    assert app.config["DEBUG"] is False


def test_production_requires_non_dev_secret(monkeypatch):
    monkeypatch.setenv("SPORT_TRACKER_DEBUG", "false")
    monkeypatch.delenv("SPORT_TRACKER_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError):
        create_app({"TESTING": False})
