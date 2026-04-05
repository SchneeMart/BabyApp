from flask import Blueprint, render_template, jsonify, request, send_file
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Gesundheit, GesundheitFoto, Impfung, Medikament, Arztbesuch
from src.utils import check_kind_zugriff, get_erstellt_von
from datetime import datetime, date
from io import BytesIO

gesundheit_bp = Blueprint('gesundheit', __name__, url_prefix='/gesundheit')


@gesundheit_bp.route('/')
@login_required
def index():
    return render_template('gesundheit/gesundheit.html', module_name='Gesundheit')


# --- Gesundheitseinträge ---
@gesundheit_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    eintraege = Gesundheit.query.filter_by(kind_id=kind_id).order_by(Gesundheit.datum.desc()).limit(50).all()
    return jsonify([{
        'id': e.id, 'datum': e.datum.isoformat() + 'Z', 'typ': e.typ,
        'temperatur': e.temperatur, 'symptome': e.symptome,
        'beschreibung': e.beschreibung, 'notiz': e.notiz,
        'fotos': [{'id': f.id, 'dateiname': f.dateiname} for f in e.fotos],
    } for e in eintraege])


@gesundheit_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    data = request.get_json()
    kind_id = data.get('kind_id')
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    eintrag = Gesundheit(
        kind_id=kind_id, typ=data.get('typ', 'symptom'),
        datum=datetime.fromisoformat(data['datum'].replace('Z', '')) if data.get('datum') else datetime.utcnow(),
        temperatur=data.get('temperatur'), symptome=data.get('symptome'),
        beschreibung=data.get('beschreibung'), notiz=data.get('notiz'),
        erstellt_von=get_erstellt_von(),
    )
    db.session.add(eintrag)
    db.session.commit()
    return jsonify({'ok': True, 'id': eintrag.id}), 201


@gesundheit_bp.route('/api/update/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    e = db.session.get(Gesundheit, id)
    if not e:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    data = request.get_json()
    if 'datum' in data and data['datum']:
        e.datum = datetime.fromisoformat(data['datum'].replace('Z', ''))
    for f in ['typ', 'temperatur', 'symptome', 'beschreibung', 'notiz']:
        if f in data:
            setattr(e, f, data[f])
    db.session.commit()
    return jsonify({'ok': True})


@gesundheit_bp.route('/api/<int:eintrag_id>/foto', methods=['POST'])
@login_required
def api_foto_upload(eintrag_id):
    """Foto zu einem Gesundheitseintrag hochladen."""
    eintrag = db.session.get(Gesundheit, eintrag_id)
    if not eintrag:
        return jsonify({'error': 'Eintrag nicht gefunden'}), 404
    zugriff = check_kind_zugriff(eintrag.kind_id)
    if zugriff:
        return zugriff

    if 'foto' not in request.files:
        return jsonify({'error': 'Keine Datei'}), 400

    datei = request.files['foto']
    if not datei.filename:
        return jsonify({'error': 'Keine Datei ausgewählt'}), 400

    # Max. 20 Fotos pro Eintrag
    if eintrag.fotos.count() >= 20:
        return jsonify({'error': 'Maximal 20 Fotos pro Eintrag'}), 400

    # Bild lesen und komprimieren
    daten = datei.read()

    # Dateityp-Validierung: Nur echte Bilder erlauben
    try:
        from PIL import Image
        img = Image.open(BytesIO(daten))
        img.verify()  # Prüft ob es ein gültiges Bild ist
        # Nach verify() muss das Bild neu geöffnet werden
        img = Image.open(BytesIO(daten))
        img.thumbnail((1200, 1200), Image.LANCZOS)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        buf = BytesIO()
        img.save(buf, format='JPEG', quality=80, optimize=True)
        daten = buf.getvalue()
        mime = 'image/jpeg'
    except Exception:
        return jsonify({'error': 'Ungültiges Bildformat. Nur JPEG, PNG und GIF erlaubt.'}), 400

    foto = GesundheitFoto(
        gesundheit_id=eintrag_id,
        daten=daten,
        mime_type=mime,
        dateiname=datei.filename,
    )
    db.session.add(foto)
    db.session.commit()
    return jsonify({'ok': True, 'id': foto.id, 'dateiname': foto.dateiname}), 201


@gesundheit_bp.route('/api/foto/<int:foto_id>')
@login_required
def api_foto_get(foto_id):
    """Foto als Bild ausliefern."""
    foto = db.session.get(GesundheitFoto, foto_id)
    if not foto:
        return 'Nicht gefunden', 404
    eintrag = db.session.get(Gesundheit, foto.gesundheit_id)
    if eintrag:
        zugriff = check_kind_zugriff(eintrag.kind_id)
        if zugriff:
            return zugriff
    return send_file(BytesIO(foto.daten), mimetype=foto.mime_type,
                     download_name=secure_filename(foto.dateiname or f'foto_{foto_id}.jpg'))


@gesundheit_bp.route('/api/foto/<int:foto_id>', methods=['DELETE'])
@login_required
def api_foto_delete(foto_id):
    foto = db.session.get(GesundheitFoto, foto_id)
    if not foto:
        return jsonify({'error': 'Nicht gefunden'}), 404
    eintrag = db.session.get(Gesundheit, foto.gesundheit_id)
    if eintrag:
        zugriff = check_kind_zugriff(eintrag.kind_id)
        if zugriff:
            return zugriff
    db.session.delete(foto)
    db.session.commit()
    return jsonify({'ok': True})


@gesundheit_bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    e = db.session.get(Gesundheit, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(e)
    db.session.commit()
    return jsonify({'ok': True})


# --- Impfungen ---
@gesundheit_bp.route('/api/impfungen/<int:kind_id>')
@login_required
def api_impfungen(kind_id):
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    eintraege = Impfung.query.filter_by(kind_id=kind_id).order_by(Impfung.datum.desc()).all()
    return jsonify([{
        'id': e.id, 'datum': e.datum.isoformat(), 'name': e.name,
        'arzt': e.arzt, 'charge': e.charge, 'reaktion': e.reaktion,
        'naechster_termin': e.naechster_termin.isoformat() if e.naechster_termin else None,
        'notiz': e.notiz,
    } for e in eintraege])


@gesundheit_bp.route('/api/impfungen/create', methods=['POST'])
@login_required
def api_impfung_create():
    data = request.get_json()
    zugriff = check_kind_zugriff(data.get('kind_id'))
    if zugriff:
        return zugriff
    e = Impfung(
        kind_id=data['kind_id'], datum=date.fromisoformat(data['datum']),
        name=data['name'], arzt=data.get('arzt'), charge=data.get('charge'),
        reaktion=data.get('reaktion'),
        naechster_termin=date.fromisoformat(data['naechster_termin']) if data.get('naechster_termin') else None,
        notiz=data.get('notiz'),
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'ok': True, 'id': e.id}), 201


@gesundheit_bp.route('/api/impfungen/delete/<int:id>', methods=['DELETE'])
@login_required
def api_impfung_delete(id):
    e = db.session.get(Impfung, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(e)
    db.session.commit()
    return jsonify({'ok': True})


# --- Medikamente ---
@gesundheit_bp.route('/api/medikamente/<int:kind_id>')
@login_required
def api_medikamente(kind_id):
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    eintraege = Medikament.query.filter_by(kind_id=kind_id).order_by(Medikament.beginn.desc()).all()
    return jsonify([{
        'id': e.id, 'name': e.name, 'dosis': e.dosis, 'einheit': e.einheit,
        'frequenz': e.frequenz, 'beginn': e.beginn.isoformat(),
        'ende': e.ende.isoformat() if e.ende else None,
        'grund': e.grund, 'notiz': e.notiz,
    } for e in eintraege])


@gesundheit_bp.route('/api/medikamente/create', methods=['POST'])
@login_required
def api_medikament_create():
    data = request.get_json()
    zugriff = check_kind_zugriff(data.get('kind_id'))
    if zugriff:
        return zugriff
    e = Medikament(
        kind_id=data['kind_id'], name=data['name'],
        dosis=data.get('dosis'), einheit=data.get('einheit'),
        frequenz=data.get('frequenz'), beginn=date.fromisoformat(data['beginn']),
        ende=date.fromisoformat(data['ende']) if data.get('ende') else None,
        grund=data.get('grund'), notiz=data.get('notiz'),
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'ok': True, 'id': e.id}), 201


@gesundheit_bp.route('/api/medikamente/delete/<int:id>', methods=['DELETE'])
@login_required
def api_medikament_delete(id):
    e = db.session.get(Medikament, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(e)
    db.session.commit()
    return jsonify({'ok': True})


# --- Arztbesuche ---
@gesundheit_bp.route('/api/arztbesuche/<int:kind_id>')
@login_required
def api_arztbesuche(kind_id):
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    eintraege = Arztbesuch.query.filter_by(kind_id=kind_id).order_by(Arztbesuch.datum.desc()).all()
    return jsonify([{
        'id': e.id, 'datum': e.datum.isoformat() + 'Z', 'arzt': e.arzt,
        'grund': e.grund, 'diagnose': e.diagnose, 'behandlung': e.behandlung,
        'naechster_termin': e.naechster_termin.isoformat() if e.naechster_termin else None,
        'notiz': e.notiz,
    } for e in eintraege])


@gesundheit_bp.route('/api/arztbesuche/create', methods=['POST'])
@login_required
def api_arztbesuch_create():
    data = request.get_json()
    zugriff = check_kind_zugriff(data.get('kind_id'))
    if zugriff:
        return zugriff
    e = Arztbesuch(
        kind_id=data['kind_id'],
        datum=datetime.fromisoformat(data['datum'].replace('Z', '')),
        arzt=data.get('arzt'), grund=data['grund'],
        diagnose=data.get('diagnose'), behandlung=data.get('behandlung'),
        naechster_termin=date.fromisoformat(data['naechster_termin']) if data.get('naechster_termin') else None,
        notiz=data.get('notiz'),
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'ok': True, 'id': e.id}), 201


@gesundheit_bp.route('/api/arztbesuche/delete/<int:id>', methods=['DELETE'])
@login_required
def api_arztbesuch_delete(id):
    e = db.session.get(Arztbesuch, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(e)
    db.session.commit()
    return jsonify({'ok': True})
