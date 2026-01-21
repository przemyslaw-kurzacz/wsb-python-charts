"""Auth tests grouped into a class."""

from __future__ import annotations

from app.models import User


class TestAuth:
    def test_register_page_loads(self, client):
        resp = client.get("/auth/register")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Rejestracja" in html

    def test_successful_registration_creates_user(self, client, app, register_user):
        resp = register_user("newuser", "password123")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Logowanie" in html

        with app.app_context():
            user = User.get_by_username("newuser")
            assert user is not None
            assert user["username"] == "newuser"
            assert "password_hash" in user

    def test_login_success_sets_session(self, client, login_user, test_user):
        resp = login_user(test_user["username"], test_user["password"])
        assert resp.status_code == 200
        with client.session_transaction() as sess:
            assert sess.get("username") == test_user["username"]
