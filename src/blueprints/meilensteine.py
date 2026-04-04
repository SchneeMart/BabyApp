from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Meilenstein
from src.utils import check_kind_zugriff
from datetime import date

meilensteine_bp = Blueprint('meilensteine', __name__, url_prefix='/meilensteine')

# Vordefinierte Meilensteine nach Kategorie und Alter
STANDARD_MEILENSTEINE = [
    # Motorik
    {'kategorie': 'motorik', 'titel': 'Kopf heben', 'alter_monate': 1},
    {'kategorie': 'motorik', 'titel': 'Greifen', 'alter_monate': 3},
    {'kategorie': 'motorik', 'titel': 'Umdrehen', 'alter_monate': 4},
    {'kategorie': 'motorik', 'titel': 'Sitzen ohne Hilfe', 'alter_monate': 6},
    {'kategorie': 'motorik', 'titel': 'Krabbeln', 'alter_monate': 8},
    {'kategorie': 'motorik', 'titel': 'Hochziehen zum Stehen', 'alter_monate': 9},
    {'kategorie': 'motorik', 'titel': 'Erste Schritte', 'alter_monate': 12},
    {'kategorie': 'motorik', 'titel': 'Sicher laufen', 'alter_monate': 15},
    {'kategorie': 'motorik', 'titel': 'Treppen steigen', 'alter_monate': 18},
    {'kategorie': 'motorik', 'titel': 'Rennen', 'alter_monate': 24},
    # Sprache
    {'kategorie': 'sprache', 'titel': 'Erstes Lächeln', 'alter_monate': 2},
    {'kategorie': 'sprache', 'titel': 'Gurren/Brabbeln', 'alter_monate': 3},
    {'kategorie': 'sprache', 'titel': 'Lachen', 'alter_monate': 4},
    {'kategorie': 'sprache', 'titel': 'Silben (ba-ba, ma-ma)', 'alter_monate': 6},
    {'kategorie': 'sprache', 'titel': 'Mama/Papa gezielt', 'alter_monate': 10},
    {'kategorie': 'sprache', 'titel': 'Erstes Wort', 'alter_monate': 12},
    {'kategorie': 'sprache', 'titel': '10 Wörter', 'alter_monate': 18},
    {'kategorie': 'sprache', 'titel': 'Zwei-Wort-Sätze', 'alter_monate': 24},
    # Sozial
    {'kategorie': 'sozial', 'titel': 'Augenkontakt halten', 'alter_monate': 1},
    {'kategorie': 'sozial', 'titel': 'Soziales Lächeln', 'alter_monate': 2},
    {'kategorie': 'sozial', 'titel': 'Fremdeln', 'alter_monate': 8},
    {'kategorie': 'sozial', 'titel': 'Winken (Tschüss)', 'alter_monate': 10},
    {'kategorie': 'sozial', 'titel': 'Zeigen auf Dinge', 'alter_monate': 12},
    {'kategorie': 'sozial', 'titel': 'Paralleles Spielen', 'alter_monate': 18},
    # Kognitiv
    {'kategorie': 'kognitiv', 'titel': 'Gegenstand folgen mit Augen', 'alter_monate': 2},
    {'kategorie': 'kognitiv', 'titel': 'Objekt-Permanenz', 'alter_monate': 8},
    {'kategorie': 'kognitiv', 'titel': 'Kuckuck-Spiel verstehen', 'alter_monate': 9},
    {'kategorie': 'kognitiv', 'titel': 'Einfache Anweisungen verstehen', 'alter_monate': 12},
    {'kategorie': 'kognitiv', 'titel': 'Formen sortieren', 'alter_monate': 18},
    {'kategorie': 'kognitiv', 'titel': 'Farben benennen', 'alter_monate': 30},
    # Selbstständigkeit
    {'kategorie': 'selbststaendigkeit', 'titel': 'Finger-Food essen', 'alter_monate': 8},
    {'kategorie': 'selbststaendigkeit', 'titel': 'Aus Becher trinken', 'alter_monate': 12},
    {'kategorie': 'selbststaendigkeit', 'titel': 'Mit Löffel essen', 'alter_monate': 15},
    {'kategorie': 'selbststaendigkeit', 'titel': 'Schuhe ausziehen', 'alter_monate': 18},
    {'kategorie': 'selbststaendigkeit', 'titel': 'Hände waschen', 'alter_monate': 24},
    {'kategorie': 'selbststaendigkeit', 'titel': 'Töpfchen-Training begonnen', 'alter_monate': 24},
]


@meilensteine_bp.route('/')
@login_required
def index():
    return render_template('meilensteine/meilensteine.html', module_name='Meilensteine')


@meilensteine_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    eintraege = Meilenstein.query.filter_by(kind_id=kind_id).order_by(Meilenstein.kategorie, Meilenstein.alter_monate).all()
    return jsonify([{
        'id': e.id, 'kategorie': e.kategorie, 'titel': e.titel,
        'beschreibung': e.beschreibung, 'datum': e.datum.isoformat() if e.datum else None,
        'alter_monate': e.alter_monate, 'erreicht': e.erreicht, 'notiz': e.notiz,
    } for e in eintraege])


@meilensteine_bp.route('/api/init/<int:kind_id>', methods=['POST'])
@login_required
def api_init(kind_id):
    """Initialisiert die Standard-Meilensteine für ein Kind."""
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    if Meilenstein.query.filter_by(kind_id=kind_id).count() > 0:
        return jsonify({'info': 'Bereits initialisiert'}), 200

    for m in STANDARD_MEILENSTEINE:
        db.session.add(Meilenstein(
            kind_id=kind_id, kategorie=m['kategorie'],
            titel=m['titel'], alter_monate=m['alter_monate'],
        ))
    db.session.commit()
    return jsonify({'ok': True, 'count': len(STANDARD_MEILENSTEINE)}), 201


@meilensteine_bp.route('/api/toggle/<int:id>', methods=['POST'])
@login_required
def api_toggle(id):
    e = db.session.get(Meilenstein, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    data = request.get_json() or {}
    e.erreicht = not e.erreicht
    if e.erreicht and not e.datum:
        e.datum = date.today()
    if 'datum' in data and data['datum']:
        e.datum = date.fromisoformat(data['datum'])
    if 'notiz' in data:
        e.notiz = data['notiz']
    db.session.commit()
    return jsonify({'ok': True, 'erreicht': e.erreicht})


@meilensteine_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    data = request.get_json()
    zugriff = check_kind_zugriff(data.get('kind_id'))
    if zugriff:
        return zugriff
    e = Meilenstein(
        kind_id=data['kind_id'], kategorie=data.get('kategorie', 'motorik'),
        titel=data['titel'], beschreibung=data.get('beschreibung'),
        datum=date.fromisoformat(data['datum']) if data.get('datum') else None,
        alter_monate=data.get('alter_monate'), erreicht=data.get('erreicht', False),
        notiz=data.get('notiz'),
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'ok': True, 'id': e.id}), 201


@meilensteine_bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    e = db.session.get(Meilenstein, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(e)
    db.session.commit()
    return jsonify({'ok': True})
