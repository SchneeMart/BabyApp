from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Milchvorrat
from src.utils import check_kind_zugriff, get_erstellt_von
from datetime import datetime, date, timedelta

milchvorrat_bp = Blueprint('milchvorrat', __name__, url_prefix='/milchvorrat')


@milchvorrat_bp.route('/')
@login_required
def index():
    return render_template('milchvorrat/milchvorrat.html', module_name='Milchvorrat')


@milchvorrat_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    eintraege = Milchvorrat.query.filter_by(kind_id=kind_id).order_by(Milchvorrat.datum.desc()).limit(100).all()
    return jsonify([{
        'id': e.id, 'datum': e.datum.isoformat() + 'Z', 'menge_ml': e.menge_ml,
        'typ': e.typ, 'lagerort': e.lagerort, 'flasche_nr': e.flasche_nr,
        'verfallsdatum': e.verfallsdatum.isoformat() if e.verfallsdatum else None,
        'notiz': e.notiz,
    } for e in eintraege])


@milchvorrat_bp.route('/api/bestand/<int:kind_id>')
@login_required
def api_bestand(kind_id):
    """Aktueller Milchvorrat-Bestand."""
    alle = Milchvorrat.query.filter_by(kind_id=kind_id).all()
    eingelagert = sum(e.menge_ml for e in alle if e.typ == 'eingelagert')
    verbraucht = sum(e.menge_ml for e in alle if e.typ == 'verbraucht')
    entsorgt = sum(e.menge_ml for e in alle if e.typ == 'entsorgt')
    bestand = eingelagert - verbraucht - entsorgt

    # Verfallene Einträge
    heute = date.today()
    verfallen = sum(e.menge_ml for e in alle if e.typ == 'eingelagert'
                    and e.verfallsdatum and e.verfallsdatum < heute)

    # Nach Lagerort
    kuehl = sum(e.menge_ml for e in alle if e.typ == 'eingelagert' and e.lagerort == 'kuehlschrank')
    tiefkuehl = sum(e.menge_ml for e in alle if e.typ == 'eingelagert' and e.lagerort == 'tiefkuehl')
    kuehl_verbraucht = sum(e.menge_ml for e in alle if e.typ == 'verbraucht' and e.lagerort == 'kuehlschrank')
    tiefkuehl_verbraucht = sum(e.menge_ml for e in alle if e.typ == 'verbraucht' and e.lagerort == 'tiefkuehl')

    return jsonify({
        'bestand_ml': max(0, bestand),
        'eingelagert_ml': eingelagert,
        'verbraucht_ml': verbraucht,
        'entsorgt_ml': entsorgt,
        'verfallen_ml': verfallen,
        'kuehlschrank_ml': max(0, kuehl - kuehl_verbraucht),
        'tiefkuehl_ml': max(0, tiefkuehl - tiefkuehl_verbraucht),
    })


@milchvorrat_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    data = request.get_json()
    kind_id = data.get('kind_id')
    if not kind_id or not db.session.get(Kind, kind_id):
        return jsonify({'error': 'Kind nicht gefunden'}), 404
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff

    lagerort = data.get('lagerort', 'kuehlschrank')
    verfallsdatum = None
    if data.get('typ', 'eingelagert') == 'eingelagert':
        if lagerort == 'kuehlschrank':
            verfallsdatum = date.today() + timedelta(days=3)
        elif lagerort == 'tiefkuehl':
            verfallsdatum = date.today() + timedelta(days=180)
    if data.get('verfallsdatum'):
        verfallsdatum = date.fromisoformat(data['verfallsdatum'])

    eintrag = Milchvorrat(
        kind_id=kind_id,
        menge_ml=data.get('menge_ml', 0),
        typ=data.get('typ', 'eingelagert'),
        lagerort=lagerort,
        flasche_nr=data.get('flasche_nr'),
        verfallsdatum=verfallsdatum,
        notiz=data.get('notiz'),
        erstellt_von=get_erstellt_von(),
    )
    db.session.add(eintrag)
    db.session.commit()
    return jsonify({'ok': True, 'id': eintrag.id}), 201


@milchvorrat_bp.route('/api/update/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    e = db.session.get(Milchvorrat, id)
    if not e:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    data = request.get_json()
    for f in ['menge_ml', 'typ', 'lagerort', 'flasche_nr', 'notiz']:
        if f in data:
            setattr(e, f, data[f])
    if 'verfallsdatum' in data:
        e.verfallsdatum = date.fromisoformat(data['verfallsdatum']) if data['verfallsdatum'] else None
    db.session.commit()
    return jsonify({'ok': True})


@milchvorrat_bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    e = db.session.get(Milchvorrat, id)
    if not e:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(e)
    db.session.commit()
    return jsonify({'ok': True})
