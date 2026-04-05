from flask import Blueprint, render_template, jsonify, request, url_for
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Notfallinfo
from src.utils import check_kind_zugriff
import secrets

notfallinfo_bp = Blueprint('notfallinfo', __name__, url_prefix='/notfallinfo')


@notfallinfo_bp.route('/')
@login_required
def index():
    return render_template('notfallinfo/notfallinfo.html', module_name='Notfallinfo')


@notfallinfo_bp.route('/api/get/<int:kind_id>')
@login_required
def api_get(kind_id):
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    kind = db.session.get(Kind, kind_id)
    if not kind:
        return jsonify({'error': 'Kind nicht gefunden'}), 404

    info = Notfallinfo.query.filter_by(kind_id=kind_id).first()
    if not info:
        return jsonify({'exists': False, 'kind_name': kind.name, 'blutgruppe': kind.blutgruppe})

    return jsonify({
        'exists': True, 'id': info.id, 'kind_name': kind.name,
        'kinderarzt_name': info.kinderarzt_name, 'kinderarzt_telefon': info.kinderarzt_telefon,
        'kinderarzt_adresse': info.kinderarzt_adresse,
        'krankenhaus': info.krankenhaus, 'krankenhaus_telefon': info.krankenhaus_telefon,
        'versicherung': info.versicherung, 'versicherungsnummer': info.versicherungsnummer,
        'allergien': info.allergien, 'unvertraeglichkeiten': info.unvertraeglichkeiten,
        'chronische_erkrankungen': info.chronische_erkrankungen,
        'blutgruppe': info.blutgruppe or kind.blutgruppe,
        'notfallkontakt_name': info.notfallkontakt_name,
        'notfallkontakt_telefon': info.notfallkontakt_telefon,
        'notfallkontakt_beziehung': info.notfallkontakt_beziehung,
        'sonstiges': info.sonstiges,
    })


@notfallinfo_bp.route('/api/save/<int:kind_id>', methods=['POST'])
@login_required
def api_save(kind_id):
    kind = db.session.get(Kind, kind_id)
    if not kind:
        return jsonify({'error': 'Kind nicht gefunden'}), 404
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff

    data = request.get_json()
    info = Notfallinfo.query.filter_by(kind_id=kind_id).first()
    if not info:
        info = Notfallinfo(kind_id=kind_id)
        db.session.add(info)

    fields = ['kinderarzt_name', 'kinderarzt_telefon', 'kinderarzt_adresse',
              'krankenhaus', 'krankenhaus_telefon', 'versicherung', 'versicherungsnummer',
              'allergien', 'unvertraeglichkeiten', 'chronische_erkrankungen', 'blutgruppe',
              'notfallkontakt_name', 'notfallkontakt_telefon', 'notfallkontakt_beziehung', 'sonstiges']
    for f in fields:
        if f in data:
            setattr(info, f, data[f])

    db.session.commit()
    return jsonify({'ok': True, 'id': info.id})


@notfallinfo_bp.route('/api/share-token/<int:kind_id>', methods=['POST'])
@login_required
def api_share_token(kind_id):
    """Generiert einen Share-Token für die Notfallinfo."""
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    info = Notfallinfo.query.filter_by(kind_id=kind_id).first()
    if not info:
        return jsonify({'error': 'Keine Notfallinfo vorhanden'}), 404
    info.share_token = secrets.token_urlsafe(32)
    db.session.commit()
    share_url = url_for('notfallinfo.share_view', token=info.share_token, _external=True)
    return jsonify({'ok': True, 'token': info.share_token, 'url': share_url})


@notfallinfo_bp.route('/share/<string:token>')
def share_view(token):
    """Öffentlich teilbare Notfallinfo-Seite (über zufälligen Token geschützt)."""
    info = Notfallinfo.query.filter_by(share_token=token).first()
    if not info or not token:
        return 'Nicht gefunden', 404
    kind = db.session.get(Kind, info.kind_id)
    if not kind:
        return 'Nicht gefunden', 404
    return render_template('notfallinfo/share.html', kind=kind, info=info)
