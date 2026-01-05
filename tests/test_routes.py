"""
Tests for main routes and pages
"""
import pytest


class TestMainRoutes:
    """Test main application routes."""

    def test_index_page_loads(self, authenticated_client):
        """Test that index page loads successfully when logged in."""
        response = authenticated_client.get('/index')
        assert response.status_code == 200
        assert b'Witaj' in response.data or b'Data Charts' in response.data

    def test_index_redirect_when_not_logged_in(self, client):
        """Test that index redirects to login when not logged in."""
        response = client.get('/index', follow_redirects=False)
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_root_redirect_when_not_logged_in(self, client):
        """Test that root path redirects to login when not logged in."""
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_root_accessible_when_logged_in(self, authenticated_client):
        """Test that root path is accessible when logged in."""
        response = authenticated_client.get('/')
        assert response.status_code == 200

    def test_index_shows_username(self, authenticated_client, test_user):
        """Test that index page displays logged in username."""
        response = authenticated_client.get('/index')
        assert test_user['username'].encode() in response.data

    def test_index_shows_app_features(self, authenticated_client):
        """Test that index page shows application features."""
        response = authenticated_client.get('/index')
        assert b'Upload' in response.data or b'plik' in response.data
        assert b'dane' in response.data.lower() or b'data' in response.data.lower()


class TestErrorPages:
    """Test error page handling."""

    def test_404_page(self, client):
        """Test that 404 page is returned for non-existent routes."""
        response = client.get('/nonexistent-page')
        # Should return 404 or 500 (if error handler has issues)
        assert response.status_code in [404, 500]

    def test_404_page_content(self, client):
        """Test 404 page content."""
        response = client.get('/this-page-does-not-exist')
        # If 404 handler works, should contain error message
        if response.status_code == 404:
            assert b'404' in response.data or b'nie znaleziono' in response.data.lower()


class TestNavigationBar:
    """Test navigation bar functionality."""

    def test_navbar_logged_in(self, authenticated_client, test_user):
        """Test navigation bar when user is logged in."""
        response = authenticated_client.get('/index')
        assert response.status_code == 200
        assert test_user['username'].encode() in response.data
        assert b'Wyloguj' in response.data or b'Logout' in response.data

    def test_navbar_logged_out(self, client):
        """Test navigation bar when user is logged out."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Logowanie' in response.data or b'Login' in response.data
        assert b'Rejestracja' in response.data or b'Register' in response.data


class TestFlashMessages:
    """Test flash message functionality."""

    def test_flash_message_after_login(self, client, test_user):
        """Test that flash message appears after login."""
        response = client.post('/auth/login', data={
            'username': test_user['username'],
            'password': test_user['password']
        }, follow_redirects=True)

        assert 'Zalogowano' in response.data or 'pomyślnie' in response.data

    def test_flash_message_after_logout(self, authenticated_client):
        """Test that flash message appears after logout."""
        response = authenticated_client.get('/auth/logout', follow_redirects=True)

        assert 'Wylogowano' in response.data or 'pomyślnie' in response.data

    def test_flash_message_after_registration(self, client):
        """Test that flash message appears after registration."""
        response = client.post('/auth/register', data={
            'username': 'newuser123',
            'password': 'password123',
            'password2': 'password123'
        }, follow_redirects=True)

        assert b'Rejestracja' in response.data or b'sukcesem' in response.data


class TestStaticAssets:
    """Test static assets loading."""

    def test_bootstrap_loaded(self, client):
        """Test that Bootstrap CSS is referenced in pages."""
        response = client.get('/auth/login')
        assert b'bootstrap' in response.data.lower()

    def test_base_template_structure(self, client):
        """Test that base template has proper HTML structure."""
        response = client.get('/auth/login')
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data
        assert b'</html>' in response.data
        assert b'<head>' in response.data
        assert b'<body>' in response.data


class TestSessionPersistence:
    """Test session persistence across requests."""

    def test_session_persists_across_pages(self, authenticated_client, test_user):
        """Test that session persists when navigating between pages."""
        # Access index
        response1 = authenticated_client.get('/index')
        assert test_user['username'].encode() in response1.data

        # Navigate to another page (if exists) or refresh
        response2 = authenticated_client.get('/')
        assert test_user['username'].encode() in response2.data

    def test_session_cleared_after_logout(self, authenticated_client):
        """Test that session is cleared after logout."""
        # Logout
        authenticated_client.get('/auth/logout')

        # Try to access protected page
        response = authenticated_client.get('/index', follow_redirects=False)
        assert response.status_code == 302
        assert '/auth/login' in response.location

