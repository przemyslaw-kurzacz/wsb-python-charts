from flask import render_template, redirect, url_for, flash, session, request
from app.auth import bp
from app.auth.forms import RegistrationForm, LoginForm
from app.models import User


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user_id = User.create_user(form.username.data, form.password.data)
        if user_id:
            flash('Rejestracja zakończona sukcesem! Możesz się teraz zalogować.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Wystąpił błąd podczas rejestracji. Spróbuj ponownie.', 'danger')

    return render_template('auth/register.html', title='Rejestracja', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        if User.verify_password(form.username.data, form.password.data):
            session['username'] = form.username.data
            session.permanent = True
            flash('Zalogowano pomyślnie!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Nieprawidłowy login lub hasło', 'danger')

    return render_template('auth/login.html', title='Logowanie', form=form)


@bp.route('/logout')
def logout():
    session.pop('username', None)
    flash('Wylogowano pomyślnie', 'info')
    return redirect(url_for('auth.login'))

