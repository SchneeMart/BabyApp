from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Fuetterung
from src.utils import check_kind_zugriff, get_erstellt_von
from datetime import datetime, date

fuetterung_bp = Blueprint('fuetterung', __name__, url_prefix='/fuetterung')


@fuetterung_bp.route('/')
@login_required
def index():
    return render_template('fuetterung/fuetterung.html', module_name='Fütterung')


@fuetterung_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    datum_str = request.args.get('datum', date.today().isoformat())
    try:
        datum = date.fromisoformat(datum_str)
    except ValueError:
        datum = date.today()

    start = datetime.combine(datum, datetime.min.time())
    end = datetime.combine(datum, datetime.max.time())

    eintraege = Fuetterung.query.filter(
        Fuetterung.kind_id == kind_id,
        Fuetterung.beginn >= start,
        Fuetterung.beginn <= end
    ).order_by(Fuetterung.beginn.desc()).all()

    return jsonify([{
        'id': e.id,
        'typ': e.typ,
        'beginn': e.beginn.isoformat() + 'Z',
        'ende': e.ende.isoformat() + 'Z' if e.ende else None,
        'dauer_minuten': e.dauer_minuten,
        'seite': e.seite,
        'letzte_seite': e.letzte_seite,
        'menge_ml': e.menge_ml,
        'inhalt': e.inhalt,
        'lebensmittel': e.lebensmittel,
        'reaktion': e.reaktion,
        'notiz': e.notiz,
    } for e in eintraege])


@fuetterung_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    data = request.get_json()
    kind_id = data.get('kind_id')
    if not kind_id or not db.session.get(Kind, kind_id):
        return jsonify({'error': 'Kind nicht gefunden'}), 404
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff

    # Bei Timer-Start (kein Ende): prüfe ob schon ein Timer läuft
    if not data.get('ende'):
        from src.models import Schlaf, Aktivitaet
        if Fuetterung.query.filter(Fuetterung.kind_id == kind_id, Fuetterung.ende.is_(None)).first():
            return jsonify({'error': 'Es läuft bereits eine Fütterung'}), 400
        if Schlaf.query.filter(Schlaf.kind_id == kind_id, Schlaf.ende.is_(None)).first():
            return jsonify({'error': 'Es läuft bereits ein Schlaf-Timer. Bitte zuerst beenden.'}), 400

    eintrag = Fuetterung(
        kind_id=kind_id,
        typ=data.get('typ', 'stillen'),
        beginn=datetime.fromisoformat(data['beginn'].replace('Z', '')) if data.get('beginn') else datetime.utcnow(),
        ende=datetime.fromisoformat(data['ende'].replace('Z', '')) if data.get('ende') else None,
        dauer_minuten=data.get('dauer_minuten'),
        seite=data.get('seite'),
        letzte_seite=data.get('letzte_seite'),
        menge_ml=data.get('menge_ml'),
        inhalt=data.get('inhalt'),
        lebensmittel=data.get('lebensmittel'),
        reaktion=data.get('reaktion'),
        notiz=data.get('notiz'),
        erstellt_von=get_erstellt_von(),
    )
    db.session.add(eintrag)
    db.session.commit()
    return jsonify({'ok': True, 'id': eintrag.id}), 201


@fuetterung_bp.route('/api/update/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    eintrag = db.session.get(Fuetterung, id)
    if not eintrag:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(eintrag.kind_id)
    if zugriff:
        return zugriff

    data = request.get_json()
    for field in ['typ', 'seite', 'letzte_seite', 'menge_ml', 'inhalt', 'lebensmittel', 'reaktion', 'notiz', 'dauer_minuten']:
        if field in data:
            setattr(eintrag, field, data[field])
    if 'beginn' in data and data['beginn']:
        eintrag.beginn = datetime.fromisoformat(data['beginn'].replace('Z', ''))
    if 'ende' in data and data['ende']:
        eintrag.ende = datetime.fromisoformat(data['ende'].replace('Z', ''))

    db.session.commit()
    return jsonify({'ok': True})


@fuetterung_bp.route('/api/stop/<int:id>', methods=['POST'])
@login_required
def api_stop(id):
    eintrag = db.session.get(Fuetterung, id)
    if not eintrag:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(eintrag.kind_id)
    if zugriff:
        return zugriff
    eintrag.ende = datetime.utcnow()
    eintrag.dauer_minuten = int((eintrag.ende - eintrag.beginn).total_seconds() / 60)
    db.session.commit()
    return jsonify({'ok': True, 'dauer_minuten': eintrag.dauer_minuten})


@fuetterung_bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    eintrag = db.session.get(Fuetterung, id)
    if not eintrag:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(eintrag.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(eintrag)
    db.session.commit()
    return jsonify({'ok': True})
