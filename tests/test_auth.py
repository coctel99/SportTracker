from tests.conftest import get_csrf_token, login, register


def test_register_and_login_flow(client):
    response = register(client)
    assert b"Login" in response.data

    response = login(client)
    assert b"Dashboard" in response.data


def test_login_required_redirect(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_root_redirects_to_login_when_anonymous(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_rejects_missing_csrf(client):
    response = client.post(
        "/login",
        data={"email": "u@example.com", "password": "secret12"},
    )
    assert response.status_code == 400


def test_register_rejects_short_password(client):
    response = register(client, password="short")
    assert b"at least 8 characters" in response.data


def test_register_rejects_invalid_email(client):
    csrf_token = get_csrf_token(client, "/register")
    response = client.post(
        "/register",
        data={"email": "not-an-email", "password": "secret12", "csrf_token": csrf_token},
        follow_redirects=True,
    )
    assert b"valid email" in response.data


def test_duplicate_register_shows_error(client):
    register(client)
    response = register(client)
    assert b"already exists" in response.data


def test_logout(client):
    register(client)
    login(client)
    csrf_token = get_csrf_token(client, "/dashboard")
    response = client.post(
        "/logout",
        data={"csrf_token": csrf_token},
        follow_redirects=True,
    )
    assert b"Login" in response.data
