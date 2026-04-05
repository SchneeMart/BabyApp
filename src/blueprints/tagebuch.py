from flask import Blueprint, render_template, jsonify, request, send_file
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Tagebuch, TagebuchFoto
from src.utils import check_kind_zugriff, get_erstellt_von
from datetime import date
from io import BytesIO

tagebuch_bp = Blueprint('tagebuch', __name__, url_prefix='/tagebuch')


@tagebuch_bp.route('/')
@login_required
def index():
    return render_template('tagebuch/tagebuch.html', module_name='Tagebuch')


@tagebuch_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    seite = request.args.get('seite', 1, type=int)
    pro_seite = 20
    eintraege = Tagebuch.query.filter_by(kind_id=kind_id).order_by(
        Tagebuch.datum.desc()
    ).offset((seite - 1) * pro_seite).limit(pro_seite).all()

    return jsonify([{
        'id': e.id, 'datum': e.datum.isoformat(), 'titel': e.titel,
        'text': e.text, 'stimmung': e.stimmung,
        'fotos': [{'id': f.id, 'dateiname': f.dateiname} for f in e.fotos],
    } for e in eintraege])


@tagebuch_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    data = request.get_json()
    zugriff = check_kind_zugriff(data.get('kind_id'))
    if zugriff:
        return zugriff
    e = Tagebuch(
        kind_id=data['kind_id'],
        datum=date.fromisoformat(data['datum']) if data.get('datum') else date.today(),
        titel=data.get('titel'), text=data.get('text'),
        stimmung=data.get('stimmung'),
        erstellt_von=get_erstellt_von(),
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'ok': True, 'id': e.id}), 201


@tagebuch_bp.route('/api/<int:eintrag_id>/foto', methods=['POST'])
@login_required
def api_foto_upload(eintrag_id):
    eintrag = db.session.get(Tagebuch, eintrag_id)
    if not eintrag:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(eintrag.kind_id)
    if zugriff:
        return zugriff
    if 'foto' not in request.files:
        return jsonify({'error': 'Keine Datei'}), 400
    datei = request.files['foto']
    if not datei.filename:
        return jsonify({'error': 'Keine Datei'}), 400

    # Max. 20 Fotos pro Eintrag
    if eintrag.fotos.count() >= 20:
        return jsonify({'error': 'Maximal 20 Fotos pro Eintrag'}), 400

    daten = datei.read()

    # Dateityp-Validierung: Nur echte Bilder erlauben
    try:
        from PIL import Image
        img = Image.open(BytesIO(daten))
        img.verify()
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

    foto = TagebuchFoto(tagebuch_id=eintrag_id, daten=daten, mime_type=mime, dateiname=datei.filename)
    db.session.add(foto)
    db.session.commit()
    return jsonify({'ok': True, 'id': foto.id}), 201


@tagebuch_bp.route('/api/foto/<int:foto_id>')
@login_required
def api_foto_get(foto_id):
    foto = db.session.get(TagebuchFoto, foto_id)
    if not foto:
        return 'Nicht gefunden', 404
    eintrag = db.session.get(Tagebuch, foto.tagebuch_id)
    if eintrag:
        zugriff = check_kind_zugriff(eintrag.kind_id)
        if zugriff:
            return zugriff
    return send_file(BytesIO(foto.daten), mimetype=foto.mime_type,
                     download_name=foto.dateiname or f'foto_{foto_id}.jpg')


@tagebuch_bp.route('/api/foto/<int:foto_id>', methods=['DELETE'])
@login_required
def api_foto_delete(foto_id):
    foto = db.session.get(TagebuchFoto, foto_id)
    if not foto:
        return jsonify({'error': 'Nicht gefunden'}), 404
    eintrag = db.session.get(Tagebuch, foto.tagebuch_id)
    if eintrag:
        zugriff = check_kind_zugriff(eintrag.kind_id)
        if zugriff:
            return zugriff
    db.session.delete(foto)
    db.session.commit()
    return jsonify({'ok': True})


@tagebuch_bp.route('/api/update/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    e = db.session.get(Tagebuch, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    data = request.get_json()
    for f in ['titel', 'text', 'stimmung']:
        if f in data: setattr(e, f, data[f])
    if 'datum' in data: e.datum = date.fromisoformat(data['datum'])
    db.session.commit()
    return jsonify({'ok': True})


@tagebuch_bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    e = db.session.get(Tagebuch, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(e)
    db.session.commit()
    return jsonify({'ok': True})
