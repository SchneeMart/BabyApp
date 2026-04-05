from html import escape as html_escape
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from src.extensions import db, mail, limiter
from src.models import User
from flask_mail import Message
from datetime import datetime, timedelta
import secrets

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        # Case-insensitiver Vergleich
        user = User.query.filter(User.username.ilike(username)).first()

        if user and user.check_password(password) and user.is_active:
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user, remember=request.form.get('remember'))
            next_page = request.args.get('next')
            # Open-Redirect verhindern: Nur relative Pfade erlauben
            if next_page and (not next_page.startswith('/') or next_page.startswith('//')):
                next_page = None
            return redirect(next_page or url_for('main.index'))

        flash('Benutzername oder Passwort falsch.', 'error')

    return render_template('auth/login.html', module_name='Login')


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/register/<token>', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def register(token):
    user = User.query.filter_by(invite_token=token).first()
    if not user or (user.invite_expiration and user.invite_expiration < datetime.utcnow()):
        flash('Einladungslink ungültig oder abgelaufen.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')
        if len(password) < 8:
            flash('Passwort muss mindestens 8 Zeichen lang sein.', 'error')
        elif password != password2:
            flash('Passwörter stimmen nicht überein.', 'error')
        else:
            user.set_password(password)
            user.invite_token = None
            user.invite_expiration = None
            user.is_active = True
            db.session.commit()
            login_user(user)
            return redirect(url_for('main.index'))

    return render_template('auth/register.html', module_name='Registrierung', user=user)


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def request_reset():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.password_reset_token = token
            user.password_reset_expiration = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            try:
                from src.mail_template import render_mail
                msg = Message('Passwort zurücksetzen - BabyApp',
                              recipients=[user.email])
                reset_url = url_for('auth.reset_with_token', token=token, _external=True)
                msg.html = render_mail(
                    'Passwort zurücksetzen',
                    f'<p>Hallo <strong>{html_escape(user.username)}</strong>,</p>'
                    '<p>Du hast angefordert, dein Passwort zurückzusetzen. '
                    'Klicke auf den Button um ein neues Passwort zu setzen.</p>'
                    '<p>Der Link ist <strong>1 Stunde</strong> gültig.</p>',
                    button_text='Passwort zurücksetzen',
                    button_url=reset_url,
                )
                mail.send(msg)
            except Exception as e:
                import logging
                logging.error(f'Mail-Versand fehlgeschlagen (Passwort-Reset): {e}')
        flash('Falls ein Account mit dieser E-Mail existiert, wurde ein Link gesendet.', 'info')
    return render_template('auth/reset_password.html', module_name='Passwort zurücksetzen')


@auth_bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset_with_token(token):
    user = User.query.filter_by(password_reset_token=token).first()
    if not user or (user.password_reset_expiration and user.password_reset_expiration < datetime.utcnow()):
        flash('Link ungültig oder abgelaufen.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        if len(password) < 8:
            flash('Passwort muss mindestens 8 Zeichen lang sein.', 'error')
        else:
            user.set_password(password)
            user.password_reset_token = None
            user.password_reset_expiration = None
            db.session.commit()
            flash('Passwort erfolgreich geändert.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_with_token.html', module_name='Neues Passwort')
