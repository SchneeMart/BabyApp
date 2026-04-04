from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Wachstum
from src.utils import check_kind_zugriff, get_erstellt_von
from datetime import date

wachstum_bp = Blueprint('wachstum', __name__, url_prefix='/wachstum')


@wachstum_bp.route('/')
@login_required
def index():
    return render_template('wachstum/wachstum.html', module_name='Wachstum')


@wachstum_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    eintraege = Wachstum.query.filter_by(kind_id=kind_id).order_by(Wachstum.datum.desc()).all()
    return jsonify([{
        'id': e.id,
        'datum': e.datum.isoformat(),
        'gewicht_kg': e.gewicht_kg,
        'groesse_cm': e.groesse_cm,
        'kopfumfang_cm': e.kopfumfang_cm,
        'notiz': e.notiz,
    } for e in eintraege])


@wachstum_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    data = request.get_json()
    kind_id = data.get('kind_id')
    if not kind_id or not db.session.get(Kind, kind_id):
        return jsonify({'error': 'Kind nicht gefunden'}), 404
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff

    eintrag = Wachstum(
        kind_id=kind_id,
        datum=date.fromisoformat(data['datum']) if data.get('datum') else date.today(),
        gewicht_kg=data.get('gewicht_kg'),
        groesse_cm=data.get('groesse_cm'),
        kopfumfang_cm=data.get('kopfumfang_cm'),
        notiz=data.get('notiz'),
        erstellt_von=get_erstellt_von(),
    )
    db.session.add(eintrag)
    db.session.commit()
    return jsonify({'ok': True, 'id': eintrag.id}), 201


@wachstum_bp.route('/api/update/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    eintrag = db.session.get(Wachstum, id)
    if not eintrag:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(eintrag.kind_id)
    if zugriff:
        return zugriff
    data = request.get_json()
    if 'datum' in data:
        eintrag.datum = date.fromisoformat(data['datum'])
    for f in ['gewicht_kg', 'groesse_cm', 'kopfumfang_cm', 'notiz']:
        if f in data:
            setattr(eintrag, f, data[f])
    db.session.commit()
    return jsonify({'ok': True})


@wachstum_bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    eintrag = db.session.get(Wachstum, id)
    if not eintrag:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(eintrag.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(eintrag)
    db.session.commit()
    return jsonify({'ok': True})


@wachstum_bp.route('/api/perzentile/<int:kind_id>')
@login_required
def api_perzentile(kind_id):
    """WHO-Perzentil-Daten für Wachstumskurven."""
    kind = db.session.get(Kind, kind_id)
    if not kind:
        return jsonify({'error': 'Kind nicht gefunden'}), 404

    eintraege = Wachstum.query.filter_by(kind_id=kind_id).order_by(Wachstum.datum.asc()).all()
    punkte = []
    for e in eintraege:
        alter_tage = (e.datum - kind.geburtsdatum).days
        punkte.append({
            'alter_tage': alter_tage,
            'alter_monate': round(alter_tage / 30.44, 1),
            'gewicht_kg': e.gewicht_kg,
            'groesse_cm': e.groesse_cm,
            'kopfumfang_cm': e.kopfumfang_cm,
        })

    return jsonify({
        'geschlecht': kind.geschlecht,
        'fruehgeburt_wochen': kind.fruehgeburt_wochen,
        'punkte': punkte,
    })
