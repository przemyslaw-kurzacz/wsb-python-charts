"""User model tests grouped into a class."""

from __future__ import annotations

from app.models import User


class TestUserModel:
    def test_create_user_and_fetch(self, app):
        with app.app_context():
            user_id = User.create_user("alice", "secret123")
            assert user_id is not None

            user = User.get_by_username("alice")
            assert user is not None
            assert user["username"] == "alice"
            assert "password_hash" in user

    def test_create_duplicate_user_returns_none(self, app):
        with app.app_context():
            assert User.create_user("bob", "secret123") is not None
            assert User.create_user("bob", "otherpass") is None

    def test_verify_password(self, app):
        with app.app_context():
            User.create_user("carol", "pass123")
            assert User.verify_password("carol", "pass123") is True
            assert User.verify_password("carol", "wrong") is False
            assert User.verify_password("missing", "pass123") is False
