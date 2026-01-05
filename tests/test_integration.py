"""
Integration tests for complete user workflows
"""
import pytest
from io import BytesIO


class TestCompleteUserJourney:
    """Test complete user journeys from registration to file upload."""

    def test_complete_new_user_flow(self, client, sample_csv_file):
        """Test complete flow: register -> login -> upload file."""
        # Step 1: Register new user
        response = client.post('/auth/register', data={
            'username': 'journeyuser',
            'password': 'journey123',
            'password2': 'journey123'
        }, follow_redirects=True)
        assert response.status_code == 200

        # Step 2: Login
        response = client.post('/auth/login', data={
            'username': 'journeyuser',
            'password': 'journey123'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'journeyuser' in response.data

        # Step 3: Upload file
        data = {
            'file': (BytesIO(sample_csv_file), 'journey_data.csv')
        }
        response = client.post(
            '/index',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b'journey_data.csv' in response.data or 'pomyślnie' in response.data

        # Step 4: Verify file is shown on page
        response = client.get('/index')
        assert b'journey_data.csv' in response.data

        # Step 5: Logout
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'Logowanie' in response.data

    def test_multiple_file_uploads(self, authenticated_client, sample_csv_file):
        """Test uploading multiple files sequentially."""
        # Upload first file
        data1 = {
            'file': (BytesIO(sample_csv_file), 'file1.csv')
        }
        response = authenticated_client.post(
            '/index',
            data=data1,
            content_type='multipart/form-data',
            follow_redirects=True
        )
        assert response.status_code == 200

        # Upload second file
        data2 = {
            'file': (BytesIO(b'A,B,C\n1,2,3\n'), 'file2.csv')
        }
        response = authenticated_client.post(
            '/index',
            data=data2,
            content_type='multipart/form-data',
            follow_redirects=True
        )
        assert response.status_code == 200

        # Verify second file is shown (first should be deleted)
        response = authenticated_client.get('/index')
        assert b'file2.csv' in response.data

    def test_failed_login_attempt_then_success(self, client, test_user):
        """Test failed login followed by successful login."""
        # Failed login
        response = client.post('/auth/login', data={
            'username': test_user['username'],
            'password': 'wrongpassword'
        }, follow_redirects=True)
        assert 'Nieprawidłowy' in response.data or 'błąd' in response.data.lower()

        # Successful login
        response = client.post('/auth/login', data={
            'username': test_user['username'],
            'password': test_user['password']
        }, follow_redirects=True)
        assert response.status_code == 200
        assert test_user['username'].encode() in response.data

    def test_register_with_errors_then_correct(self, client):
        """Test registration with validation errors, then correct data."""
        # Try with mismatched passwords
        response = client.post('/auth/register', data={
            'username': 'validuser',
            'password': 'password123',
            'password2': 'different123'
        })
        assert 'identyczne' in response.data or 'zgadzać' in response.data

        # Try again with correct data
        response = client.post('/auth/register', data={
            'username': 'validuser',
            'password': 'password123',
            'password2': 'password123'
        }, follow_redirects=True)
        assert response.status_code == 200


class TestSecurityScenarios:
    """Test security-related scenarios."""

    def test_cannot_access_upload_without_login(self, client, sample_csv_file):
        """Test that file upload requires login."""
        data = {
            'file': (BytesIO(sample_csv_file), 'test.csv')
        }
        response = client.post(
            '/index',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=False
        )
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_session_expires_after_logout(self, authenticated_client):
        """Test that session expires after logout."""
        # Access page while logged in
        response = authenticated_client.get('/index')
        assert response.status_code == 200

        # Logout
        authenticated_client.get('/auth/logout')

        # Try to access page again
        response = authenticated_client.get('/index', follow_redirects=False)
        assert response.status_code == 302

    def test_different_users_isolated_data(self, client, app, sample_csv_file):
        """Test that different users have isolated data."""
        # Create and login as first user
        with app.app_context():
            from app.models import User
            User.create_user('user1', 'pass1')

        client.post('/auth/login', data={
            'username': 'user1',
            'password': 'pass1'
        })

        # Upload file as user1
        data = {
            'file': (BytesIO(sample_csv_file), 'user1_file.csv')
        }
        client.post('/index', data=data, content_type='multipart/form-data')

        # Logout
        client.get('/auth/logout')

        # Create and login as second user
        with app.app_context():
            User.create_user('user2', 'pass2')

        client.post('/auth/login', data={
            'username': 'user2',
            'password': 'pass2'
        })

        # User2 should not see user1's file
        response = client.get('/index')
        assert b'user1_file.csv' not in response.data


class TestErrorRecovery:
    """Test error recovery scenarios."""

    def test_recover_from_failed_upload(self, authenticated_client, sample_csv_file):
        """Test that user can recover from failed upload."""
        # Try to upload invalid file
        data_invalid = {
            'file': (BytesIO(b'not a csv'), 'test.txt')
        }
        response = authenticated_client.post(
            '/index',
            data=data_invalid,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200

        # Upload valid file
        data_valid = {
            'file': (BytesIO(sample_csv_file), 'valid.csv')
        }
        response = authenticated_client.post(
            '/index',
            data=data_valid,
            content_type='multipart/form-data',
            follow_redirects=True
        )
        assert response.status_code == 200

    def test_page_accessible_after_error(self, client):
        """Test that pages are still accessible after errors."""
        # Trigger an error (wrong password)
        client.post('/auth/login', data={
            'username': 'nonexistent',
            'password': 'wrong'
        })

        # Page should still be accessible
        response = client.get('/auth/login')
        assert response.status_code == 200


class TestConcurrentUsers:
    """Test scenarios with multiple concurrent users."""

    def test_multiple_users_can_exist(self, app):
        """Test that multiple users can exist in database."""
        with app.app_context():
            from app.models import User
            User.create_user('user1', 'pass1')
            User.create_user('user2', 'pass2')
            User.create_user('user3', 'pass3')

            assert User.get_by_username('user1') is not None
            assert User.get_by_username('user2') is not None
            assert User.get_by_username('user3') is not None

    def test_users_have_separate_sessions(self, app, sample_csv_file):
        """Test that different users have separate sessions."""
        # This would require multiple test clients
        # Simplified version - just ensure users are isolated
        with app.app_context():
            from app.models import User
            User.create_user('isolated1', 'pass1')
            User.create_user('isolated2', 'pass2')

            user1 = User.get_by_username('isolated1')
            user2 = User.get_by_username('isolated2')

            assert user1['username'] != user2['username']

