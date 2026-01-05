import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # TinyDB (NoSQL) configuration
    DATABASE_PATH = os.path.join(basedir, 'data', 'db.json')

    # Upload configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

