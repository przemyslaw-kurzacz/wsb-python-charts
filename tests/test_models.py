"""
Tests for User model and database operations
"""
import pytest
from app.models import User


class TestUserModel:
    """Test User model functionality."""

    def test_create_user(self, app):
        """Test creating a new user."""
        with app.app_context():
            user_id = User.create_user('testuser123', 'password123')
            assert user_id is not None

            # Verify user exists
            user = User.get_by_username('testuser123')
            assert user is not None
            assert user['username'] == 'testuser123'

    def test_create_duplicate_user(self, app):
        """Test that creating duplicate user returns None."""
        with app.app_context():
            # Create first user
            User.create_user('duplicate', 'password123')

            # Try to create duplicate
            result = User.create_user('duplicate', 'password456')
            assert result is None

    def test_get_by_username_existing(self, app, test_user):
        """Test getting existing user by username."""
        with app.app_context():
            user = User.get_by_username(test_user['username'])
            assert user is not None
            assert user['username'] == test_user['username']
            assert 'password_hash' in user

    def test_get_by_username_nonexistent(self, app):
        """Test getting nonexistent user returns None."""
        with app.app_context():
            user = User.get_by_username('nonexistent_user')
            assert user is None

    def test_verify_password_correct(self, app, test_user):
        """Test verifying correct password."""
        with app.app_context():
            result = User.verify_password(test_user['username'], test_user['password'])
            assert result is True

    def test_verify_password_incorrect(self, app, test_user):
        """Test verifying incorrect password."""
        with app.app_context():
            result = User.verify_password(test_user['username'], 'wrongpassword')
            assert result is False

    def test_verify_password_nonexistent_user(self, app):
        """Test verifying password for nonexistent user."""
        with app.app_context():
            result = User.verify_password('nonexistent', 'password')
            assert result is False

    def test_password_is_hashed(self, app):
        """Test that passwords are stored as hashes, not plaintext."""
        with app.app_context():
            password = 'mypassword123'
            User.create_user('hashtest', password)

            user = User.get_by_username('hashtest')
            # Password should be hashed, not stored in plaintext
            assert user['password_hash'] != password
            assert len(user['password_hash']) > len(password)

    def test_different_users_different_hashes(self, app):
        """Test that same password creates different hashes (salt)."""
        with app.app_context():
            password = 'samepassword'
            User.create_user('user1', password)
            User.create_user('user2', password)

            user1 = User.get_by_username('user1')
            user2 = User.get_by_username('user2')

            # Even with same password, hashes should be different (due to salt)
            assert user1['password_hash'] != user2['password_hash']


class TestDatabaseOperations:
    """Test database operations."""

    def test_database_file_created(self, app):
        """Test that database file is created."""
        with app.app_context():
            User.create_user('testuser', 'password')
            assert os.path.exists(app.config['DATABASE_PATH'])

    def test_database_isolation_between_tests(self, app):
        """Test that each test has isolated database."""
        with app.app_context():
            # This should not see users from other tests
            user = User.get_by_username('user_from_another_test')
            assert user is None


import os

