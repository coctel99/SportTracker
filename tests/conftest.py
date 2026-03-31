import os
import re
import tempfile
from pathlib import Path

import pytest

from app import create_app
from app.db import get_db, init_db


@pytest.fixture()
def app():
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)  # close the file descriptor; SQLite will manage the file

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test",
            "DATABASE": db_path,
        }
    )

    with app.app_context():
        init_db()

    yield app

    Path(db_path).unlink(missing_ok=True)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    with app.app_context():
        yield get_db()


def register(
    client, email="u@example.com", password="secret12", name="Test User", sex="male"
):
    csrf_token = get_csrf_token(client, "/register")
    return client.post(
        "/register",
        data={
            "email": email,
            "password": password,
            "name": name,
            "sex": sex,
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )


def login(client, email="u@example.com", password="secret12"):
    csrf_token = get_csrf_token(client, "/login")
    return client.post(
        "/login",
        data={"email": email, "password": password, "csrf_token": csrf_token},
        follow_redirects=True,
    )


def get_csrf_token(client, path):
    response = client.get(path)
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert match is not None
    return match.group(1).decode()
