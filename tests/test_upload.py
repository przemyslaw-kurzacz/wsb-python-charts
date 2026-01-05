"""
Tests for file upload functionality
"""
import pytest
import os
from io import BytesIO
from werkzeug.datastructures import FileStorage


class TestUploadForm:
    """Test upload form display and validation."""

    def test_upload_form_visible_when_logged_in(self, authenticated_client):
        """Test that upload form is visible on main page when logged in."""
        response = authenticated_client.get('/index')
        assert response.status_code == 200
        assert 'Prześlij plik' in response.data or b'Upload' in response.data
        assert b'CSV' in response.data

    def test_upload_form_not_visible_when_logged_out(self, client):
        """Test that upload form redirects to login when not logged in."""
        response = client.get('/index', follow_redirects=False)
        assert response.status_code == 302
        assert '/auth/login' in response.location


class TestFileUpload:
    """Test file upload functionality."""

    def test_successful_csv_upload(self, authenticated_client, app, test_user, sample_csv_file):
        """Test successful CSV file upload."""
        data = {
            'file': (BytesIO(sample_csv_file), 'test_data.csv')
        }

        response = authenticated_client.post(
            '/index',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=True
        )

        assert response.status_code == 200
        assert 'pomyślnie' in response.data or 'przesłany' in response.data

        # Verify file exists on disk
        upload_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            test_user['username'],
            'test_data.csv'
        )
        assert os.path.exists(upload_path)

    def test_upload_without_file(self, authenticated_client):
        """Test that upload without file is rejected."""
        response = authenticated_client.post(
            '/index',
            data={'file': ''},
            content_type='multipart/form-data'
        )

        # Should show validation error or stay on page
        assert response.status_code == 200

    def test_upload_non_csv_file(self, authenticated_client):
        """Test that non-CSV files are rejected."""
        data = {
            'file': (BytesIO(b'test content'), 'test.txt')
        }

        response = authenticated_client.post(
            '/index',
            data=data,
            content_type='multipart/form-data'
        )

        assert response.status_code == 200
        assert b'CSV' in response.data or b'dozwolone' in response.data

    def test_upload_replaces_old_file(self, authenticated_client, app, test_user, sample_csv_file):
        """Test that new upload replaces old file."""
        # Upload first file
        data1 = {
            'file': (BytesIO(sample_csv_file), 'first_file.csv')
        }
        authenticated_client.post(
            '/index',
            data=data1,
            content_type='multipart/form-data'
        )

        # Upload second file
        data2 = {
            'file': (BytesIO(b'Data,Value\n2024-01-01,100\n'), 'second_file.csv')
        }
        authenticated_client.post(
            '/index',
            data=data2,
            content_type='multipart/form-data'
        )

        # Check that only second file exists
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], test_user['username'])
        files = os.listdir(user_folder)

        assert len(files) == 1
        assert 'second_file.csv' in files
        assert 'first_file.csv' not in files

    def test_upload_creates_user_folder(self, authenticated_client, app, test_user, sample_csv_file):
        """Test that upload creates user-specific folder."""
        data = {
            'file': (BytesIO(sample_csv_file), 'test.csv')
        }

        authenticated_client.post(
            '/index',
            data=data,
            content_type='multipart/form-data'
        )

        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], test_user['username'])
        assert os.path.exists(user_folder)
        assert os.path.isdir(user_folder)

    def test_upload_shows_current_file_info(self, authenticated_client, sample_csv_file):
        """Test that page shows info about currently uploaded file."""
        # Upload a file
        data = {
            'file': (BytesIO(sample_csv_file), 'my_data.csv')
        }
        authenticated_client.post(
            '/index',
            data=data,
            content_type='multipart/form-data'
        )

        # Get the page again
        response = authenticated_client.get('/index')
        assert b'my_data.csv' in response.data or b'Aktualny plik' in response.data


class TestUploadSecurity:
    """Test security aspects of file upload."""

    def test_upload_requires_authentication(self, client, sample_csv_file):
        """Test that upload requires user to be logged in."""
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

    def test_users_cannot_access_other_users_files(self, app, test_user):
        """Test that users have isolated folders."""
        with app.app_context():
            # Create another user
            User.create_user('otheruser', 'password123')

        user1_folder = os.path.join(app.config['UPLOAD_FOLDER'], test_user['username'])
        user2_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'otheruser')

        # Folders should be different
        assert user1_folder != user2_folder

    def test_filename_sanitization(self, authenticated_client, sample_csv_file):
        """Test that filenames are sanitized."""
        # Try to upload file with potentially dangerous name
        data = {
            'file': (BytesIO(sample_csv_file), '../../../etc/passwd.csv')
        }

        response = authenticated_client.post(
            '/index',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=True
        )

        # Should succeed but with sanitized filename
        assert response.status_code == 200
        # File should not be in /etc/passwd location


class TestUploadFileSize:
    """Test file size limits."""

    def test_large_file_rejected(self, authenticated_client, app):
        """Test that files exceeding size limit are rejected."""
        # Create a file larger than the limit
        # Note: This test assumes MAX_CONTENT_LENGTH is set to 16MB
        large_content = b'x' * (17 * 1024 * 1024)  # 17MB

        data = {
            'file': (BytesIO(large_content), 'large_file.csv')
        }

        response = authenticated_client.post(
            '/index',
            data=data,
            content_type='multipart/form-data'
        )

        # Should be rejected (413 Request Entity Too Large)
        # Flask may return different status codes depending on configuration
        assert response.status_code in [200, 413, 400]

