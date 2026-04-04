from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Zahn
from src.utils import check_kind_zugriff
from datetime import date

zahnung_bp = Blueprint('zahnung', __name__, url_prefix='/zahnung')

# Milchzahn-Definitionen (20 Stück)
MILCHZAEHNE = [
    {'nr': 1,  'name': 'Oberer rechter mittlerer Schneidezahn', 'position': 'oben-rechts'},
    {'nr': 2,  'name': 'Oberer rechter seitlicher Schneidezahn', 'position': 'oben-rechts'},
    {'nr': 3,  'name': 'Oberer rechter Eckzahn', 'position': 'oben-rechts'},
    {'nr': 4,  'name': 'Oberer rechter erster Backenzahn', 'position': 'oben-rechts'},
    {'nr': 5,  'name': 'Oberer rechter zweiter Backenzahn', 'position': 'oben-rechts'},
    {'nr': 6,  'name': 'Oberer linker mittlerer Schneidezahn', 'position': 'oben-links'},
    {'nr': 7,  'name': 'Oberer linker seitlicher Schneidezahn', 'position': 'oben-links'},
    {'nr': 8,  'name': 'Oberer linker Eckzahn', 'position': 'oben-links'},
    {'nr': 9,  'name': 'Oberer linker erster Backenzahn', 'position': 'oben-links'},
    {'nr': 10, 'name': 'Oberer linker zweiter Backenzahn', 'position': 'oben-links'},
    {'nr': 11, 'name': 'Unterer linker mittlerer Schneidezahn', 'position': 'unten-links'},
    {'nr': 12, 'name': 'Unterer linker seitlicher Schneidezahn', 'position': 'unten-links'},
    {'nr': 13, 'name': 'Unterer linker Eckzahn', 'position': 'unten-links'},
    {'nr': 14, 'name': 'Unterer linker erster Backenzahn', 'position': 'unten-links'},
    {'nr': 15, 'name': 'Unterer linker zweiter Backenzahn', 'position': 'unten-links'},
    {'nr': 16, 'name': 'Unterer rechter mittlerer Schneidezahn', 'position': 'unten-rechts'},
    {'nr': 17, 'name': 'Unterer rechter seitlicher Schneidezahn', 'position': 'unten-rechts'},
    {'nr': 18, 'name': 'Unterer rechter Eckzahn', 'position': 'unten-rechts'},
    {'nr': 19, 'name': 'Unterer rechter erster Backenzahn', 'position': 'unten-rechts'},
    {'nr': 20, 'name': 'Unterer rechter zweiter Backenzahn', 'position': 'unten-rechts'},
]


@zahnung_bp.route('/')
@login_required
def index():
    return render_template('zahnung/zahnung.html', module_name='Zahnung', milchzaehne=MILCHZAEHNE)


@zahnung_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    eintraege = Zahn.query.filter_by(kind_id=kind_id).order_by(Zahn.zahn_nr).all()
    erfasst = {e.zahn_nr: {
        'id': e.id, 'zahn_nr': e.zahn_nr, 'name': e.name, 'position': e.position,
        'durchbruch_datum': e.durchbruch_datum.isoformat() if e.durchbruch_datum else None,
        'ausfall_datum': e.ausfall_datum.isoformat() if e.ausfall_datum else None,
        'notiz': e.notiz,
    } for e in eintraege}
    return jsonify({'erfasst': erfasst, 'gesamt': 20, 'anzahl': len(erfasst)})


@zahnung_bp.route('/api/upsert', methods=['POST'])
@login_required
def api_upsert():
    data = request.get_json()
    kind_id = data['kind_id']
    zahn_nr = data['zahn_nr']
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff

    eintrag = Zahn.query.filter_by(kind_id=kind_id, zahn_nr=zahn_nr).first()
    if not eintrag:
        zahn_def = next((z for z in MILCHZAEHNE if z['nr'] == zahn_nr), None)
        if not zahn_def:
            return jsonify({'error': 'Ungültige Zahnnummer'}), 400
        eintrag = Zahn(kind_id=kind_id, zahn_nr=zahn_nr, name=zahn_def['name'], position=zahn_def['position'])
        db.session.add(eintrag)

    if 'durchbruch_datum' in data:
        eintrag.durchbruch_datum = date.fromisoformat(data['durchbruch_datum']) if data['durchbruch_datum'] else None
    if 'ausfall_datum' in data:
        eintrag.ausfall_datum = date.fromisoformat(data['ausfall_datum']) if data['ausfall_datum'] else None
    if 'notiz' in data:
        eintrag.notiz = data['notiz']

    db.session.commit()
    return jsonify({'ok': True, 'id': eintrag.id})


@zahnung_bp.route('/api/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete(id):
    e = db.session.get(Zahn, id)
    if not e: return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    db.session.delete(e)
    db.session.commit()
    return jsonify({'ok': True})
