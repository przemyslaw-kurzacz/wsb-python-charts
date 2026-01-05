"""
Tests for application configuration
"""
import pytest
import os


class TestConfiguration:
    """Test application configuration."""

    def test_testing_mode_enabled(self, app):
        """Test that TESTING mode is enabled in test config."""
        assert app.config['TESTING'] is True

    def test_csrf_disabled_in_tests(self, app):
        """Test that CSRF is disabled for testing."""
        assert app.config['WTF_CSRF_ENABLED'] is False

    def test_database_path_configured(self, app):
        """Test that database path is configured."""
        assert 'DATABASE_PATH' in app.config
        assert app.config['DATABASE_PATH'] is not None

    def test_upload_folder_configured(self, app):
        """Test that upload folder is configured."""
        assert 'UPLOAD_FOLDER' in app.config
        assert os.path.exists(app.config['UPLOAD_FOLDER'])

    def test_secret_key_configured(self, app):
        """Test that secret key is configured."""
        assert 'SECRET_KEY' in app.config
        assert app.config['SECRET_KEY'] is not None

    def test_max_content_length_configured(self, app):
        """Test that max content length is configured."""
        assert 'MAX_CONTENT_LENGTH' in app.config


class TestBlueprintRegistration:
    """Test that all blueprints are registered."""

    def test_auth_blueprint_registered(self, app):
        """Test that auth blueprint is registered."""
        assert 'auth' in app.blueprints

    def test_main_blueprint_registered(self, app):
        """Test that main blueprint is registered."""
        assert 'main' in app.blueprints

    def test_errors_blueprint_registered(self, app):
        """Test that errors blueprint is registered."""
        assert 'errors' in app.blueprints


class TestAppFactory:
    """Test application factory pattern."""

    def test_app_creation(self):
        """Test that app can be created."""
        from app import create_app
        app = create_app()
        assert app is not None

    def test_app_name(self, app):
        """Test that app has correct name."""
        assert app.name == 'app'

    def test_app_has_context(self, app):
        """Test that app has application context."""
        with app.app_context():
            from flask import current_app
            assert current_app is app

