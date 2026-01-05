"""
Test configuration and fixtures for Data Charts App
"""
import pytest
import os
import tempfile
import shutil
from app import create_app
from app.models import User


@pytest.fixture
def app():
    """Create and configure a test Flask application instance."""
    # Create a temporary directory for uploads and database
    test_dir = tempfile.mkdtemp()

    app = create_app()
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
        'DATABASE_PATH': os.path.join(test_dir, 'test_db.json'),
        'UPLOAD_FOLDER': os.path.join(test_dir, 'uploads'),
        'SECRET_KEY': 'test-secret-key'
    })

    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    yield app

    # Cleanup after tests
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def test_user(app):
    """Create a test user in the database."""
    with app.app_context():
        username = 'testuser'
        password = 'testpass123'
        User.create_user(username, password)
        return {'username': username, 'password': password}


@pytest.fixture
def authenticated_client(client, test_user):
    """Create a client with an authenticated session."""
    client.post('/auth/login', data={
        'username': test_user['username'],
        'password': test_user['password']
    })
    return client


@pytest.fixture
def sample_csv_file():
    """Create a sample CSV file for testing."""
    csv_content = b'Data,Produkt,Sprzedaz,Koszt,Zysk\n2024-01-01,Laptop,1200,800,400\n2024-01-02,Mysz,45,20,25\n'
    return csv_content

