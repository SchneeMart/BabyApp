from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import User

profil_bp = Blueprint('profil', __name__, url_prefix='/profil')


@profil_bp.route('/')
@login_required
def index():
    return render_template('profil/profil.html', module_name='Mein Profil')


@profil_bp.route('/api/me')
@login_required
def api_me():
    """Gibt die eigenen Profildaten zurück."""
    if hasattr(current_user, 'kind_id') and isinstance(current_user.id, str) and current_user.id.startswith('token_'):
        return jsonify({
            'id': current_user.id,
            'username': 'Gast',
            'email': None,
            'rolle': 'gast',
            'rolle_label': 'Gast',
            'kann_schreiben': current_user.kann_schreiben,
            'kann_kind_erstellen': False,
            'is_admin': False,
            'last_login': None,
            'created_at': None,
        })
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'rolle': current_user.role,
        'rolle_label': current_user.rolle_label,
        'kann_schreiben': current_user.kann_schreiben,
        'kann_kind_erstellen': current_user.kann_kind_erstellen,
        'is_admin': current_user.is_admin,
        'last_login': current_user.last_login.isoformat() + 'Z' if current_user.last_login else None,
        'created_at': current_user.created_at.isoformat() + 'Z' if current_user.created_at else None,
    })


@profil_bp.route('/api/update', methods=['PUT'])
@login_required
def api_update():
    """Eigene Profildaten ändern."""
    data = request.get_json()

    if 'username' in data:
        new_name = data['username'].strip()
        if not new_name:
            return jsonify({'error': 'Benutzername darf nicht leer sein'}), 400
        existing = User.query.filter(User.username.ilike(new_name), User.id != current_user.id).first()
        if existing:
            return jsonify({'error': 'Benutzername bereits vergeben'}), 409
        current_user.username = new_name

    if 'email' in data:
        new_email = data['email'].strip().lower()
        if not new_email or '@' not in new_email:
            return jsonify({'error': 'Ungültige E-Mail-Adresse'}), 400
        existing = User.query.filter(User.email == new_email, User.id != current_user.id).first()
        if existing:
            return jsonify({'error': 'E-Mail bereits vergeben'}), 409
        current_user.email = new_email

    db.session.commit()
    return jsonify({'ok': True})


@profil_bp.route('/api/passwort', methods=['POST'])
@login_required
def api_passwort():
    """Eigenes Passwort ändern."""
    data = request.get_json()
    aktuell = data.get('aktuell', '')
    neu = data.get('neu', '')
    neu2 = data.get('neu2', '')

    if not current_user.check_password(aktuell):
        return jsonify({'error': 'Aktuelles Passwort ist falsch'}), 400
    if len(neu) < 8:
        return jsonify({'error': 'Neues Passwort muss mindestens 8 Zeichen haben'}), 400
    if neu != neu2:
        return jsonify({'error': 'Passwörter stimmen nicht überein'}), 400

    current_user.set_password(neu)
    db.session.commit()
    return jsonify({'ok': True})
