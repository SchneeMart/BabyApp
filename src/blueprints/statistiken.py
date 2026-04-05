from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from src.extensions import db
from src.models import Kind, Fuetterung, Schlaf, Windel, Wachstum
from src.utils import check_kind_zugriff
from datetime import datetime, date, timedelta
from sqlalchemy import func

statistiken_bp = Blueprint('statistiken', __name__, url_prefix='/statistiken')


@statistiken_bp.route('/')
@login_required
def index():
    return render_template('statistiken/statistiken.html', module_name='Statistiken')


@statistiken_bp.route('/api/tagesuebersicht/<int:kind_id>')
@login_required
def api_tagesuebersicht(kind_id):
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

    fuetterungen = Fuetterung.query.filter(Fuetterung.kind_id == kind_id, Fuetterung.beginn >= start, Fuetterung.beginn <= end).all()
    schlaf = Schlaf.query.filter(Schlaf.kind_id == kind_id, Schlaf.beginn >= start, Schlaf.beginn <= end).all()
    windeln = Windel.query.filter(Windel.kind_id == kind_id, Windel.zeitpunkt >= start, Windel.zeitpunkt <= end).all()

    # Fütterungsstatistik
    stillen_count = sum(1 for f in fuetterungen if f.typ == 'stillen')
    stillen_dauer = sum(f.dauer_minuten or 0 for f in fuetterungen if f.typ == 'stillen')
    flasche_count = sum(1 for f in fuetterungen if f.typ == 'flasche')
    flasche_menge = sum(f.menge_ml or 0 for f in fuetterungen if f.typ == 'flasche')

    # Schlafstatistik
    schlaf_gesamt = sum(s.dauer_minuten or 0 for s in schlaf)
    nickerchen_count = sum(1 for s in schlaf if s.typ == 'nickerchen')

    # Windelstatistik
    nass_count = sum(1 for w in windeln if w.typ in ['nass', 'beides'])
    stuhl_count = sum(1 for w in windeln if w.typ in ['stuhl', 'beides'])

    return jsonify({
        'datum': datum.isoformat(),
        'fuetterung': {
            'gesamt': len(fuetterungen),
            'stillen': {'count': stillen_count, 'dauer_minuten': stillen_dauer},
            'flasche': {'count': flasche_count, 'menge_ml': flasche_menge},
        },
        'schlaf': {
            'gesamt_minuten': schlaf_gesamt,
            'nickerchen': nickerchen_count,
            'eintraege': len(schlaf),
        },
        'windeln': {
            'gesamt': len(windeln),
            'nass': nass_count,
            'stuhl': stuhl_count,
        },
    })


@statistiken_bp.route('/api/wochenverlauf/<int:kind_id>')
@login_required
def api_wochenverlauf(kind_id):
    zugriff = check_kind_zugriff(kind_id)
    if zugriff:
        return zugriff
    heute = date.today()
    tage = []
    for i in range(6, -1, -1):
        tag = heute - timedelta(days=i)
        start = datetime.combine(tag, datetime.min.time())
        end = datetime.combine(tag, datetime.max.time())

        fuett = Fuetterung.query.filter(Fuetterung.kind_id == kind_id, Fuetterung.beginn >= start, Fuetterung.beginn <= end).count()
        schlaf_min = db.session.query(func.sum(Schlaf.dauer_minuten)).filter(
            Schlaf.kind_id == kind_id, Schlaf.beginn >= start, Schlaf.beginn <= end
        ).scalar() or 0
        wind = Windel.query.filter(Windel.kind_id == kind_id, Windel.zeitpunkt >= start, Windel.zeitpunkt <= end).count()

        tage.append({
            'datum': tag.isoformat(),
            'wochentag': ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][tag.weekday()],
            'fuetterungen': fuett,
            'schlaf_minuten': schlaf_min,
            'windeln': wind,
        })

    return jsonify(tage)
