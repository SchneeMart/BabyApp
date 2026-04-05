from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Routine, RoutineCheck
from src.utils import check_kind_zugriff
from datetime import date, datetime

routinen_bp = Blueprint('routinen', __name__, url_prefix='/routinen')


@routinen_bp.route('/')
@login_required
def index():
    return render_template('routinen/routinen.html', module_name='Routinen')


@routinen_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    routinen = Routine.query.filter_by(kind_id=kind_id).order_by(Routine.uhrzeit).all()
    heute = date.today()
    result = []
    for r in routinen:
        check = RoutineCheck.query.filter_by(routine_id=r.id, datum=heute).first()
        result.append({
            'id': r.id, 'name': r.name, 'beschreibung': r.beschreibung,
            'uhrzeit': r.uhrzeit, 'wochentage': r.wochentage,
            'aktiv': r.aktiv, 'erinnerung': r.erinnerung,
            'heute_erledigt': check.erledigt if check else False,
            'check_id': check.id if check else None,
        })
    return jsonify(result)


@routinen_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    data = request.get_json()
    zugriff = check_kind_zugriff(data.get('kind_id'))
    if zugriff:
        return zugriff
    r = Routine(
        kind_id=data['kind_id'], name=data['name'],
        beschreibung=data.get('beschreibung'),
        uhrzeit=data.get('uhrzeit'), wochentage=data.get('wochentage'),
        aktiv=data.get('aktiv', True), erinnerung=data.get('erinnerung', False),
        erinnerung_minuten_vorher=data.get('erinnerung_minuten_vorher', 10),
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({'ok': True, 'id': r.id}), 201


@routinen_bp.route('/api/update/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    r = db.session.get(Routine, id)
    if not r: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(r.kind_id)
    if zugriff:
        return zugriff
    data = request.get_json()
    for f in ['name', 'beschreibung', 'uhrzeit', 'wochentage', 'aktiv', 'erinnerung', 'erinnerung_minuten_vorher']:
        if f in data: setattr(r, f, data[f])
    db.session.commit()
    return jsonify({'ok': True})


@routinen_bp.route('/api/check/<int:id>', methods=['POST'])
@login_required
def api_check(id):
    r = db.session.get(Routine, id)
    if not r: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(r.kind_id)
    if zugriff:
        return zugriff
    heute = date.today()
    check = RoutineCheck.query.filter_by(routine_id=id, datum=heute).first()
    if not check:
        check = RoutineCheck(routine_id=id, datum=heute)
        db.session.add(check)
    check.erledigt = not check.erledigt
    check.erledigt_um = datetime.utcnow() if check.erledigt else None
    db.session.commit()
    return jsonify({'ok': True, 'erledigt': check.erledigt})


@routinen_bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    r = db.session.get(Routine, id)
    if not r: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(r.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(r)
    db.session.commit()
    return jsonify({'ok': True})
