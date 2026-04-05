from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Beikost
from src.utils import check_kind_zugriff
from datetime import date, timedelta

beikost_bp = Blueprint('beikost', __name__, url_prefix='/beikost')


@beikost_bp.route('/')
@login_required
def index():
    return render_template('beikost/beikost.html', module_name='Beikost')


@beikost_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    eintraege = Beikost.query.filter_by(kind_id=kind_id).order_by(Beikost.datum.desc()).limit(100).all()
    return jsonify([{
        'id': e.id, 'datum': e.datum.isoformat(), 'lebensmittel': e.lebensmittel,
        'kategorie': e.kategorie, 'menge': e.menge, 'akzeptanz': e.akzeptanz,
        'allergie_verdacht': e.allergie_verdacht, 'reaktion': e.reaktion,
        'vier_tage_test_start': e.vier_tage_test_start.isoformat() if e.vier_tage_test_start else None,
        'vier_tage_test_ok': e.vier_tage_test_ok, 'notiz': e.notiz,
    } for e in eintraege])


@beikost_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    data = request.get_json()
    zugriff = check_kind_zugriff(data.get('kind_id'))
    if zugriff:
        return zugriff
    e = Beikost(
        kind_id=data['kind_id'], lebensmittel=data['lebensmittel'],
        datum=date.fromisoformat(data['datum']) if data.get('datum') else date.today(),
        kategorie=data.get('kategorie'), menge=data.get('menge'),
        akzeptanz=data.get('akzeptanz'), allergie_verdacht=data.get('allergie_verdacht', False),
        reaktion=data.get('reaktion'),
        vier_tage_test_start=date.fromisoformat(data['vier_tage_test_start']) if data.get('vier_tage_test_start') else None,
        vier_tage_test_ok=data.get('vier_tage_test_ok'),
        notiz=data.get('notiz'),
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'ok': True, 'id': e.id}), 201


@beikost_bp.route('/api/update/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    e = db.session.get(Beikost, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff: return zugriff
    data = request.get_json()
    for f in ['lebensmittel', 'kategorie', 'menge', 'akzeptanz', 'allergie_verdacht', 'reaktion', 'vier_tage_test_ok', 'notiz']:
        if f in data: setattr(e, f, data[f])
    if 'datum' in data: e.datum = date.fromisoformat(data['datum'])
    if 'vier_tage_test_start' in data:
        e.vier_tage_test_start = date.fromisoformat(data['vier_tage_test_start']) if data['vier_tage_test_start'] else None
    db.session.commit()
    return jsonify({'ok': True})


@beikost_bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    e = db.session.get(Beikost, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff: return zugriff
    db.session.delete(e)
    db.session.commit()
    return jsonify({'ok': True})


@beikost_bp.route('/api/lebensmittel/<int:kind_id>')
@login_required
def api_lebensmittel(kind_id):
    """Alle eingeführten Lebensmittel mit Status."""
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    alle = Beikost.query.filter_by(kind_id=kind_id).all()
    lm_map = {}
    for e in alle:
        name = e.lebensmittel
        if name not in lm_map:
            lm_map[name] = {'name': name, 'kategorie': e.kategorie, 'count': 0,
                            'allergie': False, 'letzte_akzeptanz': None, 'vier_tage_ok': None}
        lm_map[name]['count'] += 1
        if e.allergie_verdacht:
            lm_map[name]['allergie'] = True
        if e.akzeptanz:
            lm_map[name]['letzte_akzeptanz'] = e.akzeptanz
        if e.vier_tage_test_ok is not None:
            lm_map[name]['vier_tage_ok'] = e.vier_tage_test_ok

    return jsonify(sorted(lm_map.values(), key=lambda x: x['name']))
