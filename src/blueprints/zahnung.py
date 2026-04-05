from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Zahn
from src.utils import check_kind_zugriff
from datetime import date

zahnung_bp = Blueprint('zahnung', __name__, url_prefix='/zahnung')

# Milchzahn-Definitionen (20 Stück) mit FDI-Nummern
# FDI: 5x = oben rechts, 6x = oben links, 7x = unten links, 8x = unten rechts
# x: 1=mittl.SZ, 2=seitl.SZ, 3=Eckzahn, 4=1.Backenzahn, 5=2.Backenzahn
MILCHZAEHNE = [
    {'nr': 1,  'fdi': 51, 'name': 'Oberer rechter mittlerer Schneidezahn', 'position': 'oben-rechts'},
    {'nr': 2,  'fdi': 52, 'name': 'Oberer rechter seitlicher Schneidezahn', 'position': 'oben-rechts'},
    {'nr': 3,  'fdi': 53, 'name': 'Oberer rechter Eckzahn', 'position': 'oben-rechts'},
    {'nr': 4,  'fdi': 54, 'name': 'Oberer rechter erster Backenzahn', 'position': 'oben-rechts'},
    {'nr': 5,  'fdi': 55, 'name': 'Oberer rechter zweiter Backenzahn', 'position': 'oben-rechts'},
    {'nr': 6,  'fdi': 61, 'name': 'Oberer linker mittlerer Schneidezahn', 'position': 'oben-links'},
    {'nr': 7,  'fdi': 62, 'name': 'Oberer linker seitlicher Schneidezahn', 'position': 'oben-links'},
    {'nr': 8,  'fdi': 63, 'name': 'Oberer linker Eckzahn', 'position': 'oben-links'},
    {'nr': 9,  'fdi': 64, 'name': 'Oberer linker erster Backenzahn', 'position': 'oben-links'},
    {'nr': 10, 'fdi': 65, 'name': 'Oberer linker zweiter Backenzahn', 'position': 'oben-links'},
    {'nr': 11, 'fdi': 71, 'name': 'Unterer linker mittlerer Schneidezahn', 'position': 'unten-links'},
    {'nr': 12, 'fdi': 72, 'name': 'Unterer linker seitlicher Schneidezahn', 'position': 'unten-links'},
    {'nr': 13, 'fdi': 73, 'name': 'Unterer linker Eckzahn', 'position': 'unten-links'},
    {'nr': 14, 'fdi': 74, 'name': 'Unterer linker erster Backenzahn', 'position': 'unten-links'},
    {'nr': 15, 'fdi': 75, 'name': 'Unterer linker zweiter Backenzahn', 'position': 'unten-links'},
    {'nr': 16, 'fdi': 81, 'name': 'Unterer rechter mittlerer Schneidezahn', 'position': 'unten-rechts'},
    {'nr': 17, 'fdi': 82, 'name': 'Unterer rechter seitlicher Schneidezahn', 'position': 'unten-rechts'},
    {'nr': 18, 'fdi': 83, 'name': 'Unterer rechter Eckzahn', 'position': 'unten-rechts'},
    {'nr': 19, 'fdi': 84, 'name': 'Unterer rechter erster Backenzahn', 'position': 'unten-rechts'},
    {'nr': 20, 'fdi': 85, 'name': 'Unterer rechter zweiter Backenzahn', 'position': 'unten-rechts'},
]

# Mapping intern -> FDI für schnellen Zugriff
FDI_MAP = {z['nr']: z['fdi'] for z in MILCHZAEHNE}


@zahnung_bp.route('/')
@login_required
def index():
    return render_template('zahnung/zahnung.html', module_name='Zahnung', milchzaehne=MILCHZAEHNE)


@zahnung_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    eintraege = Zahn.query.filter_by(kind_id=kind_id).order_by(Zahn.zahn_nr).all()
    erfasst = {e.zahn_nr: {
        'id': e.id, 'zahn_nr': e.zahn_nr, 'fdi': FDI_MAP.get(e.zahn_nr, e.zahn_nr),
        'name': e.name, 'position': e.position,
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
