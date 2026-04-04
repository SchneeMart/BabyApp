from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Aktivitaet, AktivitaetTyp
from src.utils import check_kind_zugriff, get_erstellt_von
from datetime import datetime, date

aktivitaeten_bp = Blueprint('aktivitaeten', __name__, url_prefix='/aktivitaeten')


@aktivitaeten_bp.route('/')
@login_required
def index():
    typen = AktivitaetTyp.query.order_by(AktivitaetTyp.name).all()
    return render_template('aktivitaeten/aktivitaeten.html', module_name='Aktivitäten', typen=typen)


@aktivitaeten_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    datum_str = request.args.get('datum', date.today().isoformat())
    try:
        datum = date.fromisoformat(datum_str)
    except ValueError:
        datum = date.today()

    start = datetime.combine(datum, datetime.min.time())
    end = datetime.combine(datum, datetime.max.time())

    eintraege = Aktivitaet.query.filter(
        Aktivitaet.kind_id == kind_id,
        Aktivitaet.beginn >= start,
        Aktivitaet.beginn <= end
    ).order_by(Aktivitaet.beginn.desc()).all()

    return jsonify([{
        'id': e.id,
        'typ_id': e.typ_id,
        'typ_name': e.typ.name if e.typ else '',
        'typ_icon': e.typ.icon if e.typ else '',
        'typ_farbe': e.typ.farbe if e.typ else '',
        'beginn': e.beginn.isoformat() + 'Z',
        'ende': e.ende.isoformat() + 'Z' if e.ende else None,
        'dauer_minuten': e.dauer_minuten,
        'notiz': e.notiz,
    } for e in eintraege])


@aktivitaeten_bp.route('/api/start', methods=['POST'])
@login_required
def api_start():
    data = request.get_json()
    zugriff = check_kind_zugriff(data.get('kind_id'))
    if zugriff:
        return zugriff
    eintrag = Aktivitaet(
        kind_id=data['kind_id'],
        typ_id=data['typ_id'],
        beginn=datetime.utcnow(),
        erstellt_von=get_erstellt_von(),
    )
    db.session.add(eintrag)
    db.session.commit()
    return jsonify({'ok': True, 'id': eintrag.id}), 201


@aktivitaeten_bp.route('/api/stop/<int:id>', methods=['POST'])
@login_required
def api_stop(id):
    e = db.session.get(Aktivitaet, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    e.ende = datetime.utcnow()
    e.dauer_minuten = int((e.ende - e.beginn).total_seconds() / 60)
    db.session.commit()
    return jsonify({'ok': True, 'dauer_minuten': e.dauer_minuten})


@aktivitaeten_bp.route('/api/update/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    e = db.session.get(Aktivitaet, id)
    if not e:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    data = request.get_json()
    if 'typ_id' in data:
        e.typ_id = data['typ_id']
    if 'beginn' in data and data['beginn']:
        e.beginn = datetime.fromisoformat(data['beginn'].replace('Z', ''))
    if 'ende' in data and data['ende']:
        e.ende = datetime.fromisoformat(data['ende'].replace('Z', ''))
    if 'dauer_minuten' in data:
        e.dauer_minuten = data['dauer_minuten']
    if 'notiz' in data:
        e.notiz = data['notiz']
    db.session.commit()
    return jsonify({'ok': True})


@aktivitaeten_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    data = request.get_json()
    zugriff = check_kind_zugriff(data.get('kind_id'))
    if zugriff:
        return zugriff
    e = Aktivitaet(
        kind_id=data['kind_id'], typ_id=data['typ_id'],
        beginn=datetime.fromisoformat(data['beginn'].replace('Z', '')) if data.get('beginn') else datetime.utcnow(),
        ende=datetime.fromisoformat(data['ende'].replace('Z', '')) if data.get('ende') else None,
        dauer_minuten=data.get('dauer_minuten'),
        notiz=data.get('notiz'), erstellt_von=current_user.id,
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'ok': True, 'id': e.id}), 201


@aktivitaeten_bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    e = db.session.get(Aktivitaet, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(e)
    db.session.commit()
    return jsonify({'ok': True})


# --- Aktivitätstypen verwalten ---
@aktivitaeten_bp.route('/api/typen')
@login_required
def api_typen():
    typen = AktivitaetTyp.query.order_by(AktivitaetTyp.name).all()
    return jsonify([{'id': t.id, 'name': t.name, 'icon': t.icon, 'farbe': t.farbe, 'ist_standard': t.ist_standard} for t in typen])


@aktivitaeten_bp.route('/api/typen/create', methods=['POST'])
@login_required
def api_typ_create():
    data = request.get_json()
    t = AktivitaetTyp(name=data['name'], icon=data.get('icon', 'star'), farbe=data.get('farbe', '#607D8B'))
    db.session.add(t)
    db.session.commit()
    return jsonify({'ok': True, 'id': t.id}), 201


@aktivitaeten_bp.route('/api/typen/delete/<int:id>', methods=['DELETE'])
@login_required
def api_typ_delete(id):
    t = db.session.get(AktivitaetTyp, id)
    if not t: return jsonify({'error': 'Nicht gefunden'}), 404
    if t.ist_standard: return jsonify({'error': 'Standard-Typen können nicht gelöscht werden'}), 400
    db.session.delete(t)
    db.session.commit()
    return jsonify({'ok': True})
