from tinydb import TinyDB, Query
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
import os


def get_db():
    """Get TinyDB instance"""
    db_path = current_app.config['DATABASE_PATH']
    return TinyDB(db_path)


class User:
    """User model for TinyDB"""

    @staticmethod
    def create_user(username, password):
        """Create a new user"""
        db = get_db()
        users_table = db.table('users')
        User_query = Query()

        # Check if user already exists
        if users_table.search(User_query.username == username):
            return None

        # Create user
        user_data = {
            'username': username,
            'password_hash': generate_password_hash(password)
        }
        user_id = users_table.insert(user_data)
        db.close()
        return user_id

    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        db = get_db()
        users_table = db.table('users')
        User_query = Query()
        user = users_table.search(User_query.username == username)
        db.close()
        return user[0] if user else None

    @staticmethod
    def verify_password(username, password):
        """Verify user password"""
        user = User.get_by_username(username)
        if user:
            return check_password_hash(user['password_hash'], password)
        return False

