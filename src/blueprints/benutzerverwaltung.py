from html import escape as html_escape
from flask import Blueprint, jsonify, request, render_template, url_for, current_app
from flask_login import login_required, current_user
from flask_mail import Message
from src.extensions import db, mail, limiter
from src.models import User, Permission
from datetime import datetime, timedelta
import secrets

benutzerverwaltung_bp = Blueprint('benutzerverwaltung', __name__, url_prefix='/benutzerverwaltung')

MODULES = [
    {'id': 'fuetterung', 'name': 'Fütterung'},
    {'id': 'schlaf', 'name': 'Schlaf'},
    {'id': 'windeln', 'name': 'Windeln'},
    {'id': 'wachstum', 'name': 'Wachstum'},
    {'id': 'gesundheit', 'name': 'Gesundheit'},
    {'id': 'zahnung', 'name': 'Zahnung'},
    {'id': 'meilensteine', 'name': 'Meilensteine'},
    {'id': 'aktivitaeten', 'name': 'Aktivitäten'},
    {'id': 'statistiken', 'name': 'Statistiken'},
    {'id': 'tagebuch', 'name': 'Tagebuch'},
    {'id': 'routinen', 'name': 'Routinen'},
    {'id': 'beikost', 'name': 'Beikost'},
    {'id': 'notfallinfo', 'name': 'Notfallinfo'},
]


@benutzerverwaltung_bp.route('/')
@login_required
def index():
    if not current_user.is_admin:
        return 'Keine Berechtigung', 403
    return render_template('benutzerverwaltung/benutzerverwaltung.html', module_name='Benutzerverwaltung')


@benutzerverwaltung_bp.route('/api/users')
@login_required
def api_users():
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403

    users = User.query.all()
    all_perms = Permission.query.all()
    perm_map = {}
    for p in all_perms:
        perm_map[(p.user_id, p.module_id)] = p

    result = []
    for u in users:
        perms = {}
        for m in MODULES:
            p = perm_map.get((u.id, m['id']))
            perms[m['id']] = {
                'name': m['name'],
                'read': p.can_read if p else False,
                'write': p.can_write if p else False,
            }
        result.append({
            'id': u.id, 'username': u.username, 'email': u.email,
            'role': u.role, 'is_active': u.is_active,
            'last_login': u.last_login.isoformat() + 'Z' if u.last_login else None,
            'permissions': perms,
        })
    return jsonify({'users': result, 'modules': MODULES})


@benutzerverwaltung_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def api_update_user(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Nicht gefunden'}), 404

    data = request.get_json()
    if 'username' in data:
        new_name = data['username'].strip()
        existing = User.query.filter(User.username == new_name, User.id != user_id).first()
        if existing:
            return jsonify({'error': 'Benutzername bereits vergeben'}), 409
        user.username = new_name
    if 'email' in data:
        new_email = data['email'].strip().lower()
        existing = User.query.filter(User.email == new_email, User.id != user_id).first()
        if existing:
            return jsonify({'error': 'E-Mail bereits vergeben'}), 409
        user.email = new_email
    if 'role' in data:
        user.role = data['role']

    db.session.commit()
    return jsonify({'ok': True})


@benutzerverwaltung_bp.route('/api/users/<int:user_id>/permissions', methods=['PUT'])
@login_required
def api_update_permissions(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403

    data = request.get_json()
    for module_id, perms in data.items():
        perm = Permission.query.filter_by(user_id=user_id, module_id=module_id).first()
        if not perm:
            perm = Permission(user_id=user_id, module_id=module_id)
            db.session.add(perm)
        perm.can_read = perms.get('read', False)
        perm.can_write = perms.get('write', False)
    db.session.commit()
    return jsonify({'ok': True})


@benutzerverwaltung_bp.route('/api/invite', methods=['POST'])
@limiter.limit("10 per hour")
@login_required
def api_invite():
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403

    data = request.get_json()
    email = data.get('email', '').strip().lower()
    username = data.get('username', '').strip()
    role = data.get('role', 'betreuer')

    if not email or not username:
        return jsonify({'error': 'E-Mail und Benutzername erforderlich'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'E-Mail bereits registriert'}), 409
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Benutzername bereits vergeben'}), 409

    token = secrets.token_urlsafe(32)
    user = User(
        username=username, email=email, role=role,
        password_hash='INVITE_PENDING', is_active=False,
        invite_token=token,
        invite_expiration=datetime.utcnow() + timedelta(days=7),
    )
    db.session.add(user)
    db.session.flush()

    # Alle Module standardmäßig freigeben
    schreiben = role not in ('leser',)
    for m in MODULES:
        db.session.add(Permission(user_id=user.id, module_id=m['id'], can_read=True, can_write=schreiben))
    db.session.commit()

    # E-Mail senden (nur wenn Mail-Server konfiguriert)
    invite_url = url_for('auth.register', token=token, _external=True)
    mail_server = current_app.config.get('MAIL_SERVER', '')
    if not mail_server:
        return jsonify({'ok': True, 'id': user.id, 'mail_sent': False, 'invite_url': invite_url,
                        'hinweis': 'Kein Mail-Server konfiguriert. Registrierungslink manuell weitergeben.'})
    try:
        from src.mail_template import render_mail
        msg = Message('Einladung zur BabyApp', recipients=[email])
        rollen_label = {'admin': 'Administrator', 'mutter': 'Mutter', 'vater': 'Vater', 'betreuer': 'Betreuer', 'leser': 'Leser'}
        msg.html = render_mail(
            'Du wurdest eingeladen!',
            f'<p>Hallo <strong>{html_escape(username)}</strong>,</p>'
            f'<p>Du wurdest als <strong>{html_escape(rollen_label.get(role, role))}</strong> zur BabyApp eingeladen.</p>'
            '<p>Klicke auf den Button um dein Konto zu erstellen und loszulegen.</p>'
            '<p>Der Link ist <strong>7 Tage</strong> gültig.</p>',
            button_text='Konto erstellen',
            button_url=invite_url,
        )
        mail.send(msg)
        return jsonify({'ok': True, 'id': user.id, 'mail_sent': True})
    except Exception:
        return jsonify({'ok': True, 'id': user.id, 'mail_sent': False, 'invite_url': invite_url})


@benutzerverwaltung_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403
    if user_id == current_user.id:
        return jsonify({'error': 'Eigenen Account nicht löschbar'}), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Nicht gefunden'}), 404
    # Zugehörige Freigaben löschen
    from src.models import KindFreigabe
    KindFreigabe.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({'ok': True})


@benutzerverwaltung_bp.route('/api/users/<int:user_id>/resend-invite', methods=['POST'])
@login_required
def api_resend_invite(user_id):
    """Einladungs-E-Mail erneut senden."""
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Nicht gefunden'}), 404

    # Neuen Token erstellen
    token = secrets.token_urlsafe(32)
    user.invite_token = token
    user.invite_expiration = datetime.utcnow() + timedelta(days=7)
    db.session.commit()

    invite_url = url_for('auth.register', token=token, _external=True)
    mail_server = current_app.config.get('MAIL_SERVER', '')
    if not mail_server:
        return jsonify({'ok': True, 'mail_sent': False, 'invite_url': invite_url,
                        'hinweis': 'Kein Mail-Server konfiguriert.'})
    try:
        from src.mail_template import render_mail
        rollen_label = {'admin': 'Administrator', 'mutter': 'Mutter', 'vater': 'Vater', 'betreuer': 'Betreuer', 'leser': 'Leser'}
        msg = Message('Einladung zur BabyApp', recipients=[user.email])
        msg.html = render_mail(
            'Du wurdest eingeladen!',
            f'<p>Hallo <strong>{html_escape(user.username)}</strong>,</p>'
            f'<p>Du wurdest als <strong>{html_escape(rollen_label.get(user.role, user.role))}</strong> zur BabyApp eingeladen.</p>'
            '<p>Klicke auf den Button um dein Konto zu erstellen.</p>'
            '<p>Der Link ist <strong>7 Tage</strong> gültig.</p>',
            button_text='Konto erstellen',
            button_url=invite_url,
        )
        mail.send(msg)
        return jsonify({'ok': True, 'mail_sent': True})
    except Exception:
        return jsonify({'ok': True, 'mail_sent': False, 'invite_url': invite_url})
