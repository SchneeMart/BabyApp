import csv
import io
from flask import Blueprint, render_template, jsonify, request, Response, make_response
from flask_login import login_required, current_user
from src.extensions import db
from src.models import (Kind, Fuetterung, Schlaf, Windel, Wachstum,
                        Gesundheit, Impfung, Medikament, Arztbesuch, Meilenstein)
from src.utils import check_kind_zugriff
from datetime import datetime, date, timedelta

export_bp = Blueprint('export', __name__, url_prefix='/export')


@export_bp.route('/')
@login_required
def index():
    return render_template('export/export.html', module_name='Berichte & Export')


@export_bp.route('/csv/<int:kind_id>/<string:modul>')
@login_required
def csv_export(kind_id, modul):
    """CSV-Export für ein Modul."""
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    kind = db.session.get(Kind, kind_id)
    if not kind:
        return 'Kind nicht gefunden', 404

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    if modul == 'fuetterung':
        writer.writerow(['Datum', 'Typ', 'Beginn', 'Ende', 'Dauer (Min.)', 'Seite', 'Menge (ml)', 'Inhalt', 'Lebensmittel', 'Notiz'])
        for e in Fuetterung.query.filter_by(kind_id=kind_id).order_by(Fuetterung.beginn.desc()).all():
            writer.writerow([e.beginn.strftime('%d.%m.%Y'), e.typ,
                             e.beginn.strftime('%H:%M'), e.ende.strftime('%H:%M') if e.ende else '',
                             e.dauer_minuten or '', e.seite or '', e.menge_ml or '', e.inhalt or '',
                             e.lebensmittel or '', e.notiz or ''])

    elif modul == 'schlaf':
        writer.writerow(['Datum', 'Beginn', 'Ende', 'Dauer (Min.)', 'Typ', 'Qualität', 'Ort', 'Notiz'])
        for e in Schlaf.query.filter_by(kind_id=kind_id).order_by(Schlaf.beginn.desc()).all():
            writer.writerow([e.beginn.strftime('%d.%m.%Y'), e.beginn.strftime('%H:%M'),
                             e.ende.strftime('%H:%M') if e.ende else '', e.dauer_minuten or '',
                             e.typ or '', e.qualitaet or '', e.ort or '', e.notiz or ''])

    elif modul == 'windeln':
        writer.writerow(['Datum', 'Uhrzeit', 'Typ', 'Farbe', 'Konsistenz', 'Notiz'])
        for e in Windel.query.filter_by(kind_id=kind_id).order_by(Windel.zeitpunkt.desc()).all():
            writer.writerow([e.zeitpunkt.strftime('%d.%m.%Y'), e.zeitpunkt.strftime('%H:%M'),
                             e.typ, e.farbe or '', e.konsistenz or '', e.notiz or ''])

    elif modul == 'wachstum':
        writer.writerow(['Datum', 'Gewicht (kg)', 'Größe (cm)', 'Kopfumfang (cm)', 'Notiz'])
        for e in Wachstum.query.filter_by(kind_id=kind_id).order_by(Wachstum.datum.desc()).all():
            writer.writerow([e.datum.strftime('%d.%m.%Y'), e.gewicht_kg or '', e.groesse_cm or '',
                             e.kopfumfang_cm or '', e.notiz or ''])

    elif modul == 'gesundheit':
        writer.writerow(['Datum', 'Typ', 'Temperatur', 'Symptome', 'Beschreibung', 'Notiz'])
        for e in Gesundheit.query.filter_by(kind_id=kind_id).order_by(Gesundheit.datum.desc()).all():
            writer.writerow([e.datum.strftime('%d.%m.%Y %H:%M'), e.typ, e.temperatur or '',
                             e.symptome or '', e.beschreibung or '', e.notiz or ''])

    elif modul == 'impfungen':
        writer.writerow(['Datum', 'Name', 'Arzt', 'Charge', 'Reaktion', 'Nächster Termin', 'Notiz'])
        for e in Impfung.query.filter_by(kind_id=kind_id).order_by(Impfung.datum.desc()).all():
            writer.writerow([e.datum.strftime('%d.%m.%Y'), e.name, e.arzt or '', e.charge or '',
                             e.reaktion or '', e.naechster_termin.strftime('%d.%m.%Y') if e.naechster_termin else '', e.notiz or ''])

    elif modul == 'meilensteine':
        writer.writerow(['Kategorie', 'Titel', 'Alter (Monate)', 'Erreicht', 'Datum', 'Notiz'])
        for e in Meilenstein.query.filter_by(kind_id=kind_id).order_by(Meilenstein.kategorie, Meilenstein.alter_monate).all():
            writer.writerow([e.kategorie, e.titel, e.alter_monate or '',
                             'Ja' if e.erreicht else 'Nein',
                             e.datum.strftime('%d.%m.%Y') if e.datum else '', e.notiz or ''])
    else:
        return 'Unbekanntes Modul', 400

    output.seek(0)
    dateiname = f'{kind.name}_{modul}_{date.today().strftime("%Y%m%d")}.csv'
    return Response(
        '\ufeff' + output.getvalue(),  # BOM für Excel
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{dateiname}"'}
    )


@export_bp.route('/bericht/<int:kind_id>')
@login_required
def arztbericht(kind_id):
    """HTML-Arztbericht zum Drucken/PDF-Speichern."""
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    kind = db.session.get(Kind, kind_id)
    if not kind:
        return 'Kind nicht gefunden', 404

    von = request.args.get('von')
    bis = request.args.get('bis')
    von_date = date.fromisoformat(von) if von else date.today() - timedelta(days=30)
    bis_date = date.fromisoformat(bis) if bis else date.today()
    von_dt = datetime.combine(von_date, datetime.min.time())
    bis_dt = datetime.combine(bis_date, datetime.max.time())

    fuetterungen = Fuetterung.query.filter(
        Fuetterung.kind_id == kind_id, Fuetterung.beginn >= von_dt, Fuetterung.beginn <= bis_dt
    ).order_by(Fuetterung.beginn.desc()).all()

    schlaf = Schlaf.query.filter(
        Schlaf.kind_id == kind_id, Schlaf.beginn >= von_dt, Schlaf.beginn <= bis_dt
    ).order_by(Schlaf.beginn.desc()).all()

    windeln = Windel.query.filter(
        Windel.kind_id == kind_id, Windel.zeitpunkt >= von_dt, Windel.zeitpunkt <= bis_dt
    ).order_by(Windel.zeitpunkt.desc()).all()

    wachstum = Wachstum.query.filter(
        Wachstum.kind_id == kind_id, Wachstum.datum >= von_date, Wachstum.datum <= bis_date
    ).order_by(Wachstum.datum.desc()).all()

    gesundheit = Gesundheit.query.filter(
        Gesundheit.kind_id == kind_id, Gesundheit.datum >= von_dt, Gesundheit.datum <= bis_dt
    ).order_by(Gesundheit.datum.desc()).all()

    impfungen = Impfung.query.filter_by(kind_id=kind_id).order_by(Impfung.datum.desc()).all()
    medikamente = Medikament.query.filter_by(kind_id=kind_id).order_by(Medikament.beginn.desc()).all()

    return render_template('export/bericht.html',
                           kind=kind, von=von_date, bis=bis_date,
                           fuetterungen=fuetterungen, schlaf=schlaf, windeln=windeln,
                           wachstum=wachstum, gesundheit=gesundheit,
                           impfungen=impfungen, medikamente=medikamente)
