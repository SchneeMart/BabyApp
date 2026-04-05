from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Windel
from src.utils import check_kind_zugriff, get_erstellt_von
from datetime import datetime, date

windeln_bp = Blueprint('windeln', __name__, url_prefix='/windeln')


@windeln_bp.route('/')
@login_required
def index():
    return render_template('windeln/windeln.html', module_name='Windeln')


@windeln_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    datum_str = request.args.get('datum', date.today().isoformat())
    try:
        datum = date.fromisoformat(datum_str)
    except ValueError:
        datum = date.today()

    start = datetime.combine(datum, datetime.min.time())
    end = datetime.combine(datum, datetime.max.time())

    eintraege = Windel.query.filter(
        Windel.kind_id == kind_id,
        Windel.zeitpunkt >= start,
        Windel.zeitpunkt <= end
    ).order_by(Windel.zeitpunkt.desc()).all()

    return jsonify([{
        'id': e.id,
        'zeitpunkt': e.zeitpunkt.isoformat() + 'Z',
        'typ': e.typ,
        'farbe': e.farbe,
        'konsistenz': e.konsistenz,
        'notiz': e.notiz,
    } for e in eintraege])


@windeln_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    data = request.get_json()
    kind_id = data.get('kind_id')
    if not kind_id or not db.session.get(Kind, kind_id):
        return jsonify({'error': 'Kind nicht gefunden'}), 404
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff

    eintrag = Windel(
        kind_id=kind_id,
        zeitpunkt=datetime.fromisoformat(data['zeitpunkt'].replace('Z', '')) if data.get('zeitpunkt') else datetime.utcnow(),
        typ=data.get('typ', 'nass'),
        farbe=data.get('farbe'),
        konsistenz=data.get('konsistenz'),
        notiz=data.get('notiz'),
        erstellt_von=get_erstellt_von(),
    )
    db.session.add(eintrag)
    db.session.commit()
    return jsonify({'ok': True, 'id': eintrag.id}), 201


@windeln_bp.route('/api/update/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    e = db.session.get(Windel, id)
    if not e:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    data = request.get_json()
    if 'zeitpunkt' in data and data['zeitpunkt']:
        e.zeitpunkt = datetime.fromisoformat(data['zeitpunkt'].replace('Z', ''))
    for f in ['typ', 'farbe', 'konsistenz', 'notiz']:
        if f in data:
            setattr(e, f, data[f])
    db.session.commit()
    return jsonify({'ok': True})


@windeln_bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    eintrag = db.session.get(Windel, id)
    if not eintrag:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(eintrag.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(eintrag)
    db.session.commit()
    return jsonify({'ok': True})
