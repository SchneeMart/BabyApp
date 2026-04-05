from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Schlaf, Fuetterung
from src.utils import check_kind_zugriff, get_erstellt_von
from datetime import datetime, date, timedelta

schlaf_bp = Blueprint('schlaf', __name__, url_prefix='/schlaf')


@schlaf_bp.route('/')
@login_required
def index():
    return render_template('schlaf/schlaf.html', module_name='Schlaf')


@schlaf_bp.route('/api/list/<int:kind_id>')
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

    eintraege = Schlaf.query.filter(
        Schlaf.kind_id == kind_id,
        Schlaf.beginn >= start,
        Schlaf.beginn <= end
    ).order_by(Schlaf.beginn.desc()).all()

    return jsonify([{
        'id': e.id,
        'beginn': e.beginn.isoformat() + 'Z',
        'ende': e.ende.isoformat() + 'Z' if e.ende else None,
        'dauer_minuten': e.dauer_minuten,
        'typ': e.typ,
        'qualitaet': e.qualitaet,
        'ort': e.ort,
        'notiz': e.notiz,
    } for e in eintraege])


@schlaf_bp.route('/api/start', methods=['POST'])
@login_required
def api_start():
    data = request.get_json()
    kind_id = data.get('kind_id')
    if not kind_id or not db.session.get(Kind, kind_id):
        return jsonify({'error': 'Kind nicht gefunden'}), 404
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff

    # Prüfen ob irgendein Timer läuft
    aktiv = Schlaf.query.filter(Schlaf.kind_id == kind_id, Schlaf.ende.is_(None)).first()
    if aktiv:
        return jsonify({'error': 'Es läuft bereits ein Schlaf-Timer'}), 400
    aktive_fuetterung = Fuetterung.query.filter(Fuetterung.kind_id == kind_id, Fuetterung.ende.is_(None)).first()
    if aktive_fuetterung:
        return jsonify({'error': 'Es läuft gerade eine Fütterung. Bitte zuerst beenden.'}), 400

    eintrag = Schlaf(
        kind_id=kind_id,
        beginn=datetime.utcnow(),
        typ=data.get('typ', 'nickerchen'),
        ort=data.get('ort'),
        erstellt_von=get_erstellt_von(),
    )
    db.session.add(eintrag)
    db.session.commit()
    return jsonify({'ok': True, 'id': eintrag.id, 'beginn': eintrag.beginn.isoformat() + 'Z'}), 201


@schlaf_bp.route('/api/stop/<int:id>', methods=['POST'])
@login_required
def api_stop(id):
    eintrag = db.session.get(Schlaf, id)
    if not eintrag:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(eintrag.kind_id)
    if zugriff:
        return zugriff
    eintrag.ende = datetime.utcnow()
    eintrag.dauer_minuten = max(1, round((eintrag.ende - eintrag.beginn).total_seconds() / 60))
    data = request.get_json(silent=True) or {}
    if 'qualitaet' in data:
        eintrag.qualitaet = data['qualitaet']
    if 'notiz' in data:
        eintrag.notiz = data['notiz']
    db.session.commit()
    return jsonify({'ok': True, 'dauer_minuten': eintrag.dauer_minuten})


@schlaf_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    data = request.get_json()
    kind_id = data.get('kind_id')
    if not kind_id:
        return jsonify({'error': 'kind_id fehlt'}), 400
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff

    eintrag = Schlaf(
        kind_id=kind_id,
        beginn=datetime.fromisoformat(data['beginn'].replace('Z', '')) if data.get('beginn') else datetime.utcnow(),
        ende=datetime.fromisoformat(data['ende'].replace('Z', '')) if data.get('ende') else None,
        dauer_minuten=data.get('dauer_minuten'),
        typ=data.get('typ', 'nickerchen'),
        qualitaet=data.get('qualitaet'),
        ort=data.get('ort'),
        notiz=data.get('notiz'),
        erstellt_von=get_erstellt_von(),
    )
    db.session.add(eintrag)
    db.session.commit()
    return jsonify({'ok': True, 'id': eintrag.id}), 201


@schlaf_bp.route('/api/update/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    e = db.session.get(Schlaf, id)
    if not e:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    data = request.get_json()
    if 'beginn' in data and data['beginn']:
        e.beginn = datetime.fromisoformat(data['beginn'].replace('Z', ''))
    if 'ende' in data and data['ende']:
        e.ende = datetime.fromisoformat(data['ende'].replace('Z', ''))
    for f in ['typ', 'qualitaet', 'ort', 'notiz', 'dauer_minuten']:
        if f in data:
            setattr(e, f, data[f])
    db.session.commit()
    return jsonify({'ok': True})


@schlaf_bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    eintrag = db.session.get(Schlaf, id)
    if not eintrag:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(eintrag.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(eintrag)
    db.session.commit()
    return jsonify({'ok': True})


@schlaf_bp.route('/api/vorhersage/<int:kind_id>')
@login_required
def api_vorhersage(kind_id):
    """Einfache Schlafvorhersage basierend auf den letzten 7 Tagen."""
    sieben_tage = datetime.utcnow() - timedelta(days=7)
    eintraege = Schlaf.query.filter(
        Schlaf.kind_id == kind_id,
        Schlaf.beginn >= sieben_tage,
        Schlaf.ende.isnot(None)
    ).all()

    if len(eintraege) < 3:
        return jsonify({'vorhersage': None, 'grund': 'Zu wenig Daten'})

    # Durchschnittliche Schlafzeiten berechnen
    schlafzeiten = {}
    for e in eintraege:
        stunde = e.beginn.hour
        if stunde not in schlafzeiten:
            schlafzeiten[stunde] = []
        schlafzeiten[stunde].append(e.dauer_minuten or 0)

    vorhersagen = []
    for stunde, dauern in sorted(schlafzeiten.items()):
        if len(dauern) >= 2:
            avg_dauer = sum(dauern) / len(dauern)
            vorhersagen.append({
                'stunde': stunde,
                'durchschnitt_minuten': round(avg_dauer),
                'haeufigkeit': len(dauern),
            })

    return jsonify({'vorhersage': vorhersagen})
