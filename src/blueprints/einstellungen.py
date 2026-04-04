import re
import secrets
from datetime import date
from flask import Blueprint, render_template, jsonify, request, url_for
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Einstellung, KindFreigabe, KindToken, User
from src.utils import check_kind_zugriff, check_owner_oder_admin

einstellungen_bp = Blueprint('einstellungen', __name__, url_prefix='/einstellungen')


@einstellungen_bp.route('/')
@login_required
def index():
    if not current_user.is_admin and not current_user.is_elternteil:
        return 'Kein Zugriff. Nur Mutter, Vater oder Admin.', 403
    kinder = Kind.query.order_by(Kind.name).all()
    return render_template('einstellungen/einstellungen.html', module_name='Einstellungen', kinder=kinder)


# --- Kinder verwalten ---
@einstellungen_bp.route('/api/kinder')
@login_required
def api_kinder():
    if current_user.is_admin:
        kinder = Kind.query.order_by(Kind.name).all()
    elif hasattr(current_user, 'kind_id') and isinstance(current_user.id, str) and current_user.id.startswith('token_'):
        # TokenGast: nur das freigegebene Kind
        kind = db.session.get(Kind, current_user.kind_id)
        kinder = [kind] if kind else []
    else:
        kind_ids = [f.kind_id for f in KindFreigabe.query.filter_by(user_id=current_user.id).all()]
        kinder = Kind.query.filter(Kind.id.in_(kind_ids)).order_by(Kind.name).all() if kind_ids else []
    return jsonify([{
        'id': k.id, 'name': k.name,
        'geburtsdatum': k.geburtsdatum.isoformat(),
        'geschlecht': k.geschlecht,
        'land': k.land or 'AT',
        'fruehgeburt_wochen': k.fruehgeburt_wochen,
        'blutgruppe': k.blutgruppe,
        'alter_text': k.alter_text,
    } for k in kinder])


@einstellungen_bp.route('/api/kinder/create', methods=['POST'])
@login_required
def api_kind_create():
    if not current_user.kann_kind_erstellen:
        return jsonify({'error': 'Nur Mutter, Vater oder Admin dürfen Kinder anlegen'}), 403
    data = request.get_json()
    kind = Kind(
        name=data['name'],
        geburtsdatum=date.fromisoformat(data['geburtsdatum']),
        geschlecht=data.get('geschlecht'),
        fruehgeburt_wochen=data.get('fruehgeburt_wochen'),
        blutgruppe=data.get('blutgruppe'),
    )
    db.session.add(kind)
    db.session.flush()
    # Ersteller wird automatisch Owner
    db.session.add(KindFreigabe(kind_id=kind.id, user_id=current_user.id, rolle='owner'))
    db.session.commit()
    return jsonify({'ok': True, 'id': kind.id}), 201


@einstellungen_bp.route('/api/kinder/update/<int:id>', methods=['PUT'])
@login_required
def api_kind_update(id):
    kind = db.session.get(Kind, id)
    if not kind:
        return jsonify({'error': 'Kind nicht gefunden'}), 404
    zugriff = check_owner_oder_admin(id)
    if zugriff:
        return zugriff
    data = request.get_json()
    if 'name' in data: kind.name = data['name']
    if 'geburtsdatum' in data: kind.geburtsdatum = date.fromisoformat(data['geburtsdatum'])
    if 'geschlecht' in data: kind.geschlecht = data['geschlecht']
    if 'land' in data: kind.land = data['land']
    if 'fruehgeburt_wochen' in data: kind.fruehgeburt_wochen = data['fruehgeburt_wochen']
    if 'blutgruppe' in data: kind.blutgruppe = data['blutgruppe']
    db.session.commit()
    return jsonify({'ok': True})


@einstellungen_bp.route('/api/kinder/delete/<int:id>', methods=['DELETE'])
@login_required
def api_kind_delete(id):
    kind = db.session.get(Kind, id)
    if not kind:
        return jsonify({'error': 'Kind nicht gefunden'}), 404
    zugriff = check_owner_oder_admin(id)
    if zugriff:
        return zugriff
    db.session.delete(kind)
    db.session.commit()
    return jsonify({'ok': True})


# --- App-Einstellungen ---
@einstellungen_bp.route('/api/settings')
@login_required
def api_settings():
    keys = ['site_name', 'color_primary', 'color_primary_hover', 'color_nav_bg', 'color_page_bg',
            'mail_server', 'mail_port', 'mail_sender', 'daily_summary_enabled', 'daily_summary_time']
    return jsonify({k: Einstellung.get_value(k, '') for k in keys})


ALLOWED_SETTINGS = {'site_name', 'color_primary', 'color_primary_hover', 'color_nav_bg', 'color_page_bg'}

@einstellungen_bp.route('/api/settings/update', methods=['POST'])
@login_required
def api_settings_update():
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403
    data = request.get_json()
    for key, value in data.items():
        if key not in ALLOWED_SETTINGS:
            continue
        # Farbwerte validieren (nur Hex-Farben)
        if key.startswith('color_') and not re.match(r'^#[0-9a-fA-F]{3,8}$', str(value)):
            continue
        Einstellung.set_value(key, value)
    return jsonify({'ok': True})


# --- Kind-Freigaben ---
@einstellungen_bp.route('/api/kinder/<int:kind_id>/freigaben')
@login_required
def api_freigaben(kind_id):
    """Alle Freigaben für ein Kind."""
    zugriff = check_owner_oder_admin(kind_id)
    if zugriff:
        return zugriff
    freigaben = KindFreigabe.query.filter_by(kind_id=kind_id).all()
    return jsonify([{
        'id': f.id, 'user_id': f.user_id,
        'username': f.user.username if f.user else '?',
        'email': f.user.email if f.user else '',
        'rolle': f.rolle,
    } for f in freigaben])


@einstellungen_bp.route('/api/kinder/<int:kind_id>/freigabe', methods=['POST'])
@login_required
def api_freigabe_erstellen(kind_id):
    """Kind für einen anderen Benutzer freigeben."""
    zugriff = check_owner_oder_admin(kind_id)
    if zugriff:
        return zugriff
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    rolle = data.get('rolle', 'read')
    if rolle not in ('read', 'write'):
        return jsonify({'error': 'Ungültige Rolle'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Benutzer mit dieser E-Mail nicht gefunden'}), 404

    existing = KindFreigabe.query.filter_by(kind_id=kind_id, user_id=user.id).first()
    if existing:
        existing.rolle = rolle
    else:
        db.session.add(KindFreigabe(kind_id=kind_id, user_id=user.id, rolle=rolle))
    db.session.commit()
    return jsonify({'ok': True, 'username': user.username})


@einstellungen_bp.route('/api/kinder/freigabe/<int:freigabe_id>', methods=['DELETE'])
@login_required
def api_freigabe_loeschen(freigabe_id):
    f = db.session.get(KindFreigabe, freigabe_id)
    if not f:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_owner_oder_admin(f.kind_id)
    if zugriff:
        return zugriff
    if f.rolle == 'owner':
        return jsonify({'error': 'Besitzer kann nicht entfernt werden'}), 400
    db.session.delete(f)
    db.session.commit()
    return jsonify({'ok': True})


# --- Token-Freigabe (öffentlich) ---
@einstellungen_bp.route('/api/kinder/<int:kind_id>/tokens')
@login_required
def api_tokens(kind_id):
    zugriff = check_owner_oder_admin(kind_id)
    if zugriff:
        return zugriff
    tokens = KindToken.query.filter_by(kind_id=kind_id).all()
    return jsonify([{
        'id': t.id, 'token': t.token,
        'berechtigung': t.berechtigung, 'aktiv': t.aktiv,
        'url': url_for('main.share_view', token=t.token, _external=True),
    } for t in tokens])


@einstellungen_bp.route('/api/kinder/<int:kind_id>/token', methods=['POST'])
@login_required
def api_token_erstellen(kind_id):
    zugriff = check_owner_oder_admin(kind_id)
    if zugriff:
        return zugriff
    data = request.get_json()
    berechtigung = data.get('berechtigung', 'read')
    token = secrets.token_urlsafe(24)
    t = KindToken(kind_id=kind_id, token=token, berechtigung=berechtigung, erstellt_von=current_user.id)
    db.session.add(t)
    db.session.commit()
    return jsonify({
        'ok': True, 'id': t.id, 'token': token,
        'url': url_for('main.share_view', token=token, _external=True),
    }), 201


@einstellungen_bp.route('/api/kinder/token/<int:token_id>', methods=['DELETE'])
@login_required
def api_token_loeschen(token_id):
    t = db.session.get(KindToken, token_id)
    if not t:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_owner_oder_admin(t.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(t)
    db.session.commit()
    return jsonify({'ok': True})


# --- Passwort ändern ---
@einstellungen_bp.route('/api/passwort', methods=['POST'])
@login_required
def api_passwort():
    data = request.get_json()
    if not current_user.check_password(data.get('aktuell', '')):
        return jsonify({'error': 'Aktuelles Passwort falsch'}), 400
    if len(data.get('neu', '')) < 8:
        return jsonify({'error': 'Neues Passwort muss mindestens 8 Zeichen haben'}), 400
    if data['neu'] != data.get('neu2', ''):
        return jsonify({'error': 'Passwörter stimmen nicht überein'}), 400
    current_user.set_password(data['neu'])
    db.session.commit()
    return jsonify({'ok': True})
