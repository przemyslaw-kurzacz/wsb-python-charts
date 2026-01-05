from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from app.models import User
import re


class RegistrationForm(FlaskForm):
    username = StringField('Login', validators=[
        DataRequired(message='Login jest wymagany'),
        Length(min=3, max=20, message='Login musi mieć od 3 do 20 znaków')
    ])
    password = PasswordField('Hasło', validators=[
        DataRequired(message='Hasło jest wymagane'),
        Length(min=6, message='Hasło musi mieć co najmniej 6 znaków')
    ])
    password2 = PasswordField('Powtórz hasło', validators=[
        DataRequired(message='Powtórzenie hasła jest wymagane'),
        EqualTo('password', message='Hasła muszą być identyczne')
    ])
    submit = SubmitField('Zarejestruj się')

    def validate_username(self, username):
        # Check if username contains only alphanumeric characters and underscores
        if not re.match(r'^[a-zA-Z0-9_]+$', username.data):
            raise ValidationError('Login może zawierać tylko litery, cyfry i podkreślenia')

        # Check if user already exists
        user = User.get_by_username(username.data)
        if user:
            raise ValidationError('Ten login jest już zajęty')


class LoginForm(FlaskForm):
    username = StringField('Login', validators=[
        DataRequired(message='Login jest wymagany')
    ])
    password = PasswordField('Hasło', validators=[
        DataRequired(message='Hasło jest wymagane')
    ])
    submit = SubmitField('Zaloguj się')

