"""pytest fixtures for Data Charts Flask app."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict

import pytest

from app import create_app
from app.models import User


@pytest.fixture()
def app(tmp_path: Path):
    app = create_app()

    db_path = tmp_path / "db.json"
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test-secret-key",
        DATABASE_PATH=str(db_path),
        UPLOAD_FOLDER=str(upload_dir),
        MAX_CONTENT_LENGTH=256 * 1024,  # 256KB
    )
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def register_user(client) -> Callable[[str, str, str], "pytest.Wrapper"]:
    def _register(username: str, password: str, password2: str | None = None):
        return client.post(
            "/auth/register",
            data={
                "username": username,
                "password": password,
                "password2": password2 if password2 is not None else password,
            },
            follow_redirects=True,
        )
    return _register


@pytest.fixture()
def login_user(client) -> Callable[[str, str], "pytest.Wrapper"]:
    def _login(username: str, password: str):
        return client.post(
            "/auth/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )
    return _login


@pytest.fixture()
def test_user(app) -> Dict[str, str]:
    with app.app_context():
        username = "testuser"
        password = "testpass123"
        User.create_user(username, password)
    return {"username": username, "password": password}


@pytest.fixture()
def authenticated_client(client, login_user, test_user):
    resp = login_user(test_user["username"], test_user["password"])
    assert resp.status_code == 200
    return client


@pytest.fixture()
def csv_bytes() -> Callable[[str], bytes]:
    def _csv(content: str) -> bytes:
        return content.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return _csv
