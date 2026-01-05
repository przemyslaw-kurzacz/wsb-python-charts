"""
Tests for authentication functionality (login, register, logout)
"""
import pytest
from app.models import User


class TestRegistration:
    """Test user registration functionality."""

    def test_register_page_loads(self, client):
        """Test that registration page loads successfully."""
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b'Rejestracja' in response.data
        assert b'Login' in response.data
        assert b'Has' in response.data  # Hasło

    def test_successful_registration(self, client, app):
        """Test successful user registration."""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'password': 'password123',
            'password2': 'password123'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert 'Rejestracja zakończona sukcesem' in response.data or 'zalogować' in response.data

        # Verify user exists in database
        with app.app_context():
            user = User.get_by_username('newuser')
            assert user is not None
            assert user['username'] == 'newuser'

    def test_registration_duplicate_username(self, client, test_user):
        """Test that registering with existing username fails."""
        response = client.post('/auth/register', data={
            'username': test_user['username'],
            'password': 'password123',
            'password2': 'password123'
        }, follow_redirects=True)

        assert 'zajęty' in response.data or b'istnieje' in response.data

    def test_registration_password_mismatch(self, client):
        """Test that password mismatch is caught."""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'password': 'password123',
            'password2': 'different123'
        })

        assert 'identyczne' in response.data or 'zgadzać' in response.data

    def test_registration_short_username(self, client):
        """Test that short username is rejected."""
        response = client.post('/auth/register', data={
            'username': 'ab',  # Too short
            'password': 'password123',
            'password2': 'password123'
        })

        assert response.status_code == 200
        assert b'3 do 20' in response.data or b'3-20' in response.data

    def test_registration_short_password(self, client):
        """Test that short password is rejected."""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'password': '12345',  # Too short
            'password2': '12345'
        })

        assert response.status_code == 200
        assert b'6' in response.data

    def test_registration_invalid_characters(self, client):
        """Test that invalid characters in username are rejected."""
        response = client.post('/auth/register', data={
            'username': 'user@name',  # Invalid character @
            'password': 'password123',
            'password2': 'password123'
        })

        assert response.status_code == 200
        # Should show validation error


class TestLogin:
    """Test user login functionality."""

    def test_login_page_loads(self, client):
        """Test that login page loads successfully."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Logowanie' in response.data
        assert b'Login' in response.data
        assert b'Has' in response.data  # Hasło

    def test_successful_login(self, client, test_user):
        """Test successful user login."""
        response = client.post('/auth/login', data={
            'username': test_user['username'],
            'password': test_user['password']
        }, follow_redirects=True)

        assert response.status_code == 200
        assert 'Zalogowano' in response.data or b'Witaj' in response.data

    def test_login_wrong_password(self, client, test_user):
        """Test that wrong password is rejected."""
        response = client.post('/auth/login', data={
            'username': test_user['username'],
            'password': 'wrongpassword'
        }, follow_redirects=True)

        assert 'Nieprawidłowy' in response.data or 'błąd' in response.data.lower()

    def test_login_nonexistent_user(self, client):
        """Test that nonexistent user cannot login."""
        response = client.post('/auth/login', data={
            'username': 'nonexistent',
            'password': 'password123'
        }, follow_redirects=True)

        assert 'Nieprawidłowy' in response.data or 'błąd' in response.data.lower()

    def test_login_redirect_to_next_page(self, client, test_user):
        """Test that login redirects to next page if specified."""
        response = client.post('/auth/login?next=/index', data={
            'username': test_user['username'],
            'password': test_user['password']
        }, follow_redirects=False)

        assert response.status_code == 302  # Redirect


class TestLogout:
    """Test user logout functionality."""

    def test_logout_when_logged_in(self, authenticated_client):
        """Test successful logout."""
        response = authenticated_client.get('/auth/logout', follow_redirects=True)

        assert response.status_code == 200
        assert 'Wylogowano' in response.data or b'Logowanie' in response.data

    def test_logout_redirects_to_login(self, authenticated_client):
        """Test that logout redirects to login page."""
        response = authenticated_client.get('/auth/logout', follow_redirects=False)

        assert response.status_code == 302
        assert '/auth/login' in response.location


class TestSessionManagement:
    """Test session management."""

    def test_session_persists_after_login(self, client, test_user):
        """Test that session persists after login."""
        # Login
        client.post('/auth/login', data={
            'username': test_user['username'],
            'password': test_user['password']
        })

        # Access protected page
        response = client.get('/index')
        assert response.status_code == 200
        assert test_user['username'].encode() in response.data

    def test_protected_page_requires_login(self, client):
        """Test that protected pages redirect to login."""
        response = client.get('/index', follow_redirects=False)

        assert response.status_code == 302
        assert '/auth/login' in response.location

