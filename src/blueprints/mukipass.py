from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, MuKiUntersuchung, Erinnerung
from src.utils import check_kind_zugriff
from datetime import datetime, date, timedelta

mukipass_bp = Blueprint('mukipass', __name__, url_prefix='/mukipass')

# === ÖSTERREICH: Mutter-Kind-Pass ===
UNTERSUCHUNGEN_AT = [
    {'name': 'U1', 'bezeichnung': '1. Lebenswoche (Neugeborenen-Screening)', 'von': 0, 'bis': 1},
    {'name': 'U2', 'bezeichnung': '4.-7. Lebenswoche', 'von': 4, 'bis': 7},
    {'name': 'A1', 'bezeichnung': 'Orthopädische Untersuchung (4.-7. Woche)', 'von': 4, 'bis': 7},
    {'name': 'A2', 'bezeichnung': 'HNO/Hörscreening (4.-7. Woche)', 'von': 4, 'bis': 7},
    {'name': 'A3', 'bezeichnung': 'Augenuntersuchung (10.-14. Woche)', 'von': 10, 'bis': 14},
    {'name': 'U3', 'bezeichnung': '3.-5. Lebensmonat', 'von': 12, 'bis': 20},
    {'name': 'U4', 'bezeichnung': '7.-9. Lebensmonat', 'von': 28, 'bis': 36},
    {'name': 'U5', 'bezeichnung': '10.-14. Lebensmonat', 'von': 40, 'bis': 56},
    {'name': 'U6', 'bezeichnung': '22.-26. Lebensmonat', 'von': 88, 'bis': 104},
    {'name': 'U7', 'bezeichnung': '34.-38. Lebensmonat', 'von': 136, 'bis': 152},
    {'name': 'U8', 'bezeichnung': '46.-50. Lebensmonat', 'von': 184, 'bis': 200},
    {'name': 'U9', 'bezeichnung': '58.-62. Lebensmonat', 'von': 232, 'bis': 248},
]

IMPFPLAN_AT = [
    {'name': '6-fach (1. Dosis)', 'alter_wochen': 8, 'beschreibung': 'Diphtherie, Tetanus, Pertussis, Polio, Hib, Hepatitis B'},
    {'name': 'Pneumokokken (1. Dosis)', 'alter_wochen': 8, 'beschreibung': 'Pneumokokken-Konjugatimpfstoff'},
    {'name': 'Rotaviren (1. Dosis)', 'alter_wochen': 7, 'beschreibung': 'Rotavirus-Schluckimpfung'},
    {'name': 'Rotaviren (2. Dosis)', 'alter_wochen': 11, 'beschreibung': 'Rotavirus-Schluckimpfung'},
    {'name': '6-fach (2. Dosis)', 'alter_wochen': 16, 'beschreibung': 'Diphtherie, Tetanus, Pertussis, Polio, Hib, Hepatitis B'},
    {'name': 'Pneumokokken (2. Dosis)', 'alter_wochen': 16, 'beschreibung': 'Pneumokokken-Konjugatimpfstoff'},
    {'name': '6-fach (3. Dosis)', 'alter_wochen': 40, 'beschreibung': 'Auffrischung'},
    {'name': 'Pneumokokken (3. Dosis)', 'alter_wochen': 48, 'beschreibung': 'Auffrischung'},
    {'name': 'MMR (1. Dosis)', 'alter_wochen': 40, 'beschreibung': 'Masern, Mumps, Röteln'},
    {'name': 'Varizellen', 'alter_wochen': 48, 'beschreibung': 'Windpocken'},
    {'name': 'Meningokokken C', 'alter_wochen': 52, 'beschreibung': 'Meningokokken Serogruppe C'},
    {'name': 'MMR (2. Dosis)', 'alter_wochen': 72, 'beschreibung': 'Masern, Mumps, Röteln Auffrischung'},
    {'name': 'FSME (1. Dosis)', 'alter_wochen': 52, 'beschreibung': 'Frühsommermeningoenzephalitis'},
    {'name': 'FSME (2. Dosis)', 'alter_wochen': 60, 'beschreibung': 'FSME Auffrischung'},
]

# === DEUTSCHLAND: Gelbes U-Heft (Kinderuntersuchungsheft) ===
UNTERSUCHUNGEN_DE = [
    {'name': 'U1', 'bezeichnung': 'Direkt nach der Geburt (Erstuntersuchung)', 'von': 0, 'bis': 0},
    {'name': 'U2', 'bezeichnung': '3.-10. Lebenstag (Basisuntersuchung)', 'von': 0, 'bis': 2},
    {'name': 'U3', 'bezeichnung': '4.-5. Lebenswoche (Reflexe, Hüftultraschall)', 'von': 4, 'bis': 5},
    {'name': 'U4', 'bezeichnung': '3.-4. Lebensmonat (Motorik, Sozialverhalten)', 'von': 12, 'bis': 16},
    {'name': 'U5', 'bezeichnung': '6.-7. Lebensmonat (Greifen, Drehen, Sehen)', 'von': 24, 'bis': 28},
    {'name': 'U6', 'bezeichnung': '10.-12. Lebensmonat (Beweglichkeit, Brabbeln)', 'von': 40, 'bis': 48},
    {'name': 'U7', 'bezeichnung': '21.-24. Lebensmonat (Laufen, Sprechen, Zähne)', 'von': 84, 'bis': 96},
    {'name': 'U7a', 'bezeichnung': '34.-36. Lebensmonat (Sprachentwicklung)', 'von': 136, 'bis': 144},
    {'name': 'U8', 'bezeichnung': '46.-48. Lebensmonat (Koordination, Sozialverhalten)', 'von': 184, 'bis': 192},
    {'name': 'U9', 'bezeichnung': '60.-64. Lebensmonat (Schulreife)', 'von': 240, 'bis': 256},
    {'name': 'J1', 'bezeichnung': '12.-14. Lebensjahr (Jugendgesundheitsuntersuchung)', 'von': 624, 'bis': 728},
]

IMPFPLAN_DE = [
    {'name': '6-fach (1. Dosis)', 'alter_wochen': 8, 'beschreibung': 'Diphtherie, Tetanus, Pertussis, Polio, Hib, Hepatitis B (STIKO)'},
    {'name': 'Pneumokokken (1. Dosis)', 'alter_wochen': 8, 'beschreibung': 'Pneumokokken-Konjugatimpfstoff (STIKO)'},
    {'name': 'Rotaviren (1. Dosis)', 'alter_wochen': 6, 'beschreibung': 'Rotavirus-Schluckimpfung (STIKO)'},
    {'name': 'Rotaviren (2. Dosis)', 'alter_wochen': 10, 'beschreibung': 'Rotavirus-Schluckimpfung (STIKO)'},
    {'name': '6-fach (2. Dosis)', 'alter_wochen': 12, 'beschreibung': 'Diphtherie, Tetanus, Pertussis, Polio, Hib, Hepatitis B'},
    {'name': 'Pneumokokken (2. Dosis)', 'alter_wochen': 16, 'beschreibung': 'Pneumokokken-Konjugatimpfstoff'},
    {'name': '6-fach (3. Dosis)', 'alter_wochen': 44, 'beschreibung': 'Auffrischung (ab 11. Monat, 6 Monate nach 2. Dosis)'},
    {'name': 'Pneumokokken (3. Dosis)', 'alter_wochen': 44, 'beschreibung': 'Auffrischung'},
    {'name': 'MMR (1. Dosis)', 'alter_wochen': 44, 'beschreibung': 'Masern, Mumps, Röteln (STIKO)'},
    {'name': 'Varizellen (1. Dosis)', 'alter_wochen': 44, 'beschreibung': 'Windpocken (STIKO)'},
    {'name': 'Meningokokken C', 'alter_wochen': 52, 'beschreibung': 'Meningokokken Serogruppe C (STIKO)'},
    {'name': 'MMR (2. Dosis)', 'alter_wochen': 60, 'beschreibung': 'Masern, Mumps, Röteln Auffrischung'},
    {'name': 'Varizellen (2. Dosis)', 'alter_wochen': 60, 'beschreibung': 'Windpocken Auffrischung'},
]


def get_plan(land):
    """Gibt Untersuchungs- und Impfplan für ein Land zurück."""
    if land == 'DE':
        return UNTERSUCHUNGEN_DE, IMPFPLAN_DE
    return UNTERSUCHUNGEN_AT, IMPFPLAN_AT


@mukipass_bp.route('/')
@login_required
def index():
    return render_template('mukipass/mukipass.html', module_name='Vorsorge')


@mukipass_bp.route('/api/list/<int:kind_id>')
@login_required
def api_list(kind_id):
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    kind = db.session.get(Kind, kind_id)
    if not kind:
        return jsonify({'error': 'Kind nicht gefunden'}), 404

    eintraege = MuKiUntersuchung.query.filter_by(kind_id=kind_id).order_by(MuKiUntersuchung.alter_von_wochen).all()
    return jsonify({
        'land': kind.land or 'AT',
        'land_label': 'Mutter-Kind-Pass' if (kind.land or 'AT') == 'AT' else 'Gelbes U-Heft',
        'eintraege': [{
            'id': e.id, 'name': e.name, 'bezeichnung': e.bezeichnung,
            'alter_von_wochen': e.alter_von_wochen, 'alter_bis_wochen': e.alter_bis_wochen,
            'soll_datum': e.soll_datum.isoformat() if e.soll_datum else None,
            'durchgefuehrt_am': e.durchgefuehrt_am.isoformat() if e.durchgefuehrt_am else None,
            'arzt': e.arzt, 'befund': e.befund,
            'gewicht': e.gewicht, 'groesse': e.groesse, 'kopfumfang': e.kopfumfang,
            'notiz': e.notiz,
        } for e in eintraege],
    })


@mukipass_bp.route('/api/init/<int:kind_id>', methods=['POST'])
@login_required
def api_init(kind_id):
    """Initialisiert den Vorsorgepan basierend auf dem Land des Kindes."""
    kind = db.session.get(Kind, kind_id)
    if not kind:
        return jsonify({'error': 'Kind nicht gefunden'}), 404
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff

    # Alte Einträge löschen und neu anlegen
    MuKiUntersuchung.query.filter_by(kind_id=kind_id).delete()
    db.session.flush()

    untersuchungen, _ = get_plan(kind.land or 'AT')
    for u in untersuchungen:
        soll = kind.geburtsdatum + timedelta(weeks=u['von']) if u['von'] is not None else None
        db.session.add(MuKiUntersuchung(
            kind_id=kind_id, name=u['name'], bezeichnung=u['bezeichnung'],
            alter_von_wochen=u['von'], alter_bis_wochen=u['bis'],
            soll_datum=soll,
        ))
    db.session.commit()
    plan_name = 'Mutter-Kind-Pass' if (kind.land or 'AT') == 'AT' else 'U-Heft'
    return jsonify({'ok': True, 'count': len(untersuchungen), 'plan': plan_name}), 201


@mukipass_bp.route('/api/update/<int:id>', methods=['PUT'])
@login_required
def api_update(id):
    e = db.session.get(MuKiUntersuchung, id)
    if not e:
        return jsonify({'error': 'Nicht gefunden'}), 404
    zugriff = check_kind_zugriff(e.kind_id)
    if zugriff:
        return zugriff
    data = request.get_json()
    if 'durchgefuehrt_am' in data:
        e.durchgefuehrt_am = date.fromisoformat(data['durchgefuehrt_am']) if data['durchgefuehrt_am'] else None
    for f in ['arzt', 'befund', 'gewicht', 'groesse', 'kopfumfang', 'notiz']:
        if f in data:
            setattr(e, f, data[f])
    db.session.commit()
    return jsonify({'ok': True})


@mukipass_bp.route('/api/impfplan/<int:kind_id>')
@login_required
def api_impfplan(kind_id):
    """Impfplan (AT oder DE) mit Soll-Terminen."""
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    kind = db.session.get(Kind, kind_id)
    if not kind:
        return jsonify({'error': 'Kind nicht gefunden'}), 404

    _, impfplan = get_plan(kind.land or 'AT')

    from src.models import Impfung
    bestehende = Impfung.query.filter_by(kind_id=kind_id).all()
    geimpft_namen = {i.name.lower() for i in bestehende}

    result = []
    for imp in impfplan:
        soll_datum = kind.geburtsdatum + timedelta(weeks=imp['alter_wochen'])
        erledigt = imp['name'].lower() in geimpft_namen
        result.append({
            'name': imp['name'], 'beschreibung': imp['beschreibung'],
            'alter_wochen': imp['alter_wochen'], 'soll_datum': soll_datum.isoformat(),
            'erledigt': erledigt,
        })
    plan_name = 'Österreichisches Gratisimpfprogramm' if (kind.land or 'AT') == 'AT' else 'STIKO-Empfehlungen'
    return jsonify({'impfungen': result, 'plan_name': plan_name, 'land': kind.land or 'AT'})
