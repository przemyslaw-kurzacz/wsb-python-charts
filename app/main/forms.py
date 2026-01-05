from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField


class UploadForm(FlaskForm):
    file = FileField('Plik CSV', validators=[
        FileRequired(message='Proszę wybrać plik'),
        FileAllowed(['csv'], message='Tylko pliki CSV są dozwolone')
    ])
    submit = SubmitField('Prześlij plik')

