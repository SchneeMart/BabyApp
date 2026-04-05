from flask import Blueprint, render_template, jsonify, request, send_from_directory, current_app
from flask_login import login_required, current_user
from src.extensions import db
from src.models import Kind, Fuetterung, Schlaf, Windel, KindToken
from datetime import datetime, date, timedelta
from sqlalchemy import func
import os

main_bp = Blueprint('main', __name__)


@main_bp.route('/sw.js')
def service_worker():
    """Service Worker auf Root-Ebene ausliefern (nötig für Scope '/')."""
    response = send_from_directory(
        os.path.join(current_app.root_path, 'static'),
        'sw.js', mimetype='application/javascript'
    )
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response


def get_active_kind():
    """Gibt das aktuell ausgewählte Kind zurück."""
    kind_id = request.cookies.get('active_kind_id')
    if kind_id:
        try:
            return db.session.get(Kind, int(kind_id))
        except (ValueError, TypeError):
            pass
    return Kind.query.first()


@main_bp.route('/share/<token>')
def share_view(token):
    """Token-Link: Setzt Session-Variablen, kein User wird angelegt."""
    from flask import make_response, redirect, session

    kt = KindToken.query.filter_by(token=token, aktiv=True).first()
    if not kt:
        return 'Ungültiger oder deaktivierter Link.', 404

    # Token-Daten in die Session schreiben -- kein User, kein Login
    session['token_kind_id'] = kt.kind_id
    session['token_berechtigung'] = kt.berechtigung  # 'read' oder 'write'
    session['token_value'] = token

    resp = make_response(redirect('/'))
    resp.set_cookie('active_kind_id', str(kt.kind_id), max_age=365*24*3600, httponly=True, samesite='Lax')
    return resp


@main_bp.route('/')
@login_required
def index():
    # Kinder werden aus dem Context-Processor geladen (gefiltert nach Zugriff)
    # Lokale Variable hier nicht mehr setzen, Template nutzt die globale 'kinder'
    from src.models import KindFreigabe
    if current_user.is_admin:
        kinder = Kind.query.order_by(Kind.name).all()
    elif hasattr(current_user, 'kind_id') and isinstance(current_user.id, str) and current_user.id.startswith('token_'):
        kind_obj = db.session.get(Kind, current_user.kind_id)
        kinder = [kind_obj] if kind_obj else []
    else:
        kind_ids = [f.kind_id for f in KindFreigabe.query.filter_by(user_id=current_user.id).all()]
        kinder = Kind.query.filter(Kind.id.in_(kind_ids)).order_by(Kind.name).all() if kind_ids else []
    kind = get_active_kind()
    # Sicherstellen dass das aktive Kind in der erlaubten Liste ist
    if kind and kind not in kinder and not current_user.is_admin:
        kind = kinder[0] if kinder else None
    heute = date.today()

    stats = {}
    if kind:
        heute_start = datetime.combine(heute, datetime.min.time())
        heute_ende = datetime.combine(heute, datetime.max.time())

        stats['fuetterungen_heute'] = Fuetterung.query.filter(
            Fuetterung.kind_id == kind.id,
            Fuetterung.beginn >= heute_start,
            Fuetterung.beginn <= heute_ende
        ).count()

        stats['schlaf_heute'] = Schlaf.query.filter(
            Schlaf.kind_id == kind.id,
            Schlaf.beginn >= heute_start,
            Schlaf.beginn <= heute_ende
        ).count()

        letzter_schlaf = Schlaf.query.filter_by(kind_id=kind.id).order_by(Schlaf.ende.desc()).first()
        if letzter_schlaf and letzter_schlaf.ende:
            stats['seit_letztem_schlaf'] = int((datetime.utcnow() - letzter_schlaf.ende).total_seconds() / 60)
        else:
            stats['seit_letztem_schlaf'] = None

        stats['windeln_heute'] = Windel.query.filter(
            Windel.kind_id == kind.id,
            Windel.zeitpunkt >= heute_start,
            Windel.zeitpunkt <= heute_ende
        ).count()

        letzte_fuetterung = Fuetterung.query.filter_by(kind_id=kind.id).order_by(Fuetterung.beginn.desc()).first()
        if letzte_fuetterung:
            stats['seit_letzter_fuetterung'] = int((datetime.utcnow() - letzte_fuetterung.beginn).total_seconds() / 60)
        else:
            stats['seit_letzter_fuetterung'] = None

        # Aktiver Timer (nur einer gleichzeitig)
        aktiver_schlaf = Schlaf.query.filter(Schlaf.kind_id == kind.id, Schlaf.ende.is_(None)).first()
        aktive_fuetterung = Fuetterung.query.filter(Fuetterung.kind_id == kind.id, Fuetterung.ende.is_(None)).first()
        from src.models import Aktivitaet
        aktive_aktivitaet = Aktivitaet.query.filter(Aktivitaet.kind_id == kind.id, Aktivitaet.ende.is_(None)).first()
        stats['aktiver_schlaf'] = aktiver_schlaf
        stats['aktive_fuetterung'] = aktive_fuetterung
        stats['aktive_aktivitaet'] = aktive_aktivitaet
        stats['timer_laeuft'] = bool(aktiver_schlaf or aktive_fuetterung or aktive_aktivitaet)

    return render_template('main/main.html',
                           module_name='Dashboard',
                           kinder=kinder,
                           kind=kind,
                           stats=stats,
                           heute=heute)


@main_bp.route('/api/aktiver-timer/<int:kind_id>')
@login_required
def api_aktiver_timer(kind_id):
    """Prüft ob gerade ein Timer läuft. Verhindert parallele Timer."""
    from src.models import Aktivitaet
    aktiver_schlaf = Schlaf.query.filter(Schlaf.kind_id == kind_id, Schlaf.ende.is_(None)).first()
    aktive_fuetterung = Fuetterung.query.filter(Fuetterung.kind_id == kind_id, Fuetterung.ende.is_(None)).first()
    aktive_aktivitaet = Aktivitaet.query.filter(Aktivitaet.kind_id == kind_id, Aktivitaet.ende.is_(None)).first()

    if aktiver_schlaf:
        return jsonify({'laeuft': True, 'typ': 'schlaf', 'id': aktiver_schlaf.id,
                        'beginn': aktiver_schlaf.beginn.isoformat() + 'Z', 'label': 'Schlaf'})
    if aktive_fuetterung:
        return jsonify({'laeuft': True, 'typ': 'fuetterung', 'id': aktive_fuetterung.id,
                        'beginn': aktive_fuetterung.beginn.isoformat() + 'Z',
                        'label': f'Fütterung ({aktive_fuetterung.typ}){" - " + aktive_fuetterung.seite if aktive_fuetterung.seite else ""}'})
    if aktive_aktivitaet:
        return jsonify({'laeuft': True, 'typ': 'aktivitaet', 'id': aktive_aktivitaet.id,
                        'beginn': aktive_aktivitaet.beginn.isoformat() + 'Z',
                        'label': aktive_aktivitaet.typ.name if aktive_aktivitaet.typ else 'Aktivität'})
    return jsonify({'laeuft': False})


@main_bp.route('/api/set-kind/<int:kind_id>', methods=['POST'])
@login_required
def set_active_kind(kind_id):
    from flask import make_response
    from src.models import KindFreigabe

    kind = db.session.get(Kind, kind_id)
    if not kind:
        return jsonify({'error': 'Kind nicht gefunden'}), 404

    # Zugriffsprüfung: Hat der User eine Freigabe für dieses Kind?
    if not current_user.is_admin:
        hat_zugriff = KindFreigabe.query.filter_by(kind_id=kind_id, user_id=current_user.id).first()
        if not hat_zugriff:
            return jsonify({'error': 'Kein Zugriff auf dieses Kind'}), 403

    resp = make_response(jsonify({'ok': True}))
    resp.set_cookie('active_kind_id', str(kind_id), max_age=365*24*3600, httponly=True, samesite='Lax')
    return resp
